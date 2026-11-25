"""Mesma coleta ingerida 2x → N linhas no raw e N mensagens na fila, não 2N (critério da Fase 1)."""

import json
import uuid
from datetime import UTC, datetime, timedelta

import psycopg
import pytest

from agrovigilance.application.ingest_weather import ingest
from agrovigilance.infrastructure.database.raw.open_meteo_events.repository import (
    OpenMeteoEventRepository,
)
from agrovigilance.infrastructure.open_meteo.client import parse_forecast
from agrovigilance.infrastructure.queues.events.publisher import EventsPublisher
from scripts.create_queues import ensure_queues
from scripts.migrate import migrate

pytestmark = pytest.mark.integration

RESPONSE = {
    "utc_offset_seconds": 0,
    "hourly_units": {"time": "iso8601", "wind_speed_10m": "km/h"},
    "hourly": {"time": ["2026-11-25T12:00", "2026-11-25T13:00"], "wind_speed_10m": [5.2, 7.9]},
}


def test_same_fetch_twice_stores_and_publishes_each_hour_once(db, sqs):
    migrate(db)
    suffix = uuid.uuid4().hex[:8]
    queue_url = ensure_queues(sqs, f"events-{suffix}", f"events-{suffix}-dlq")
    publisher = EventsPublisher(sqs, queue_url)
    fetched = datetime(2026, 11, 25, 12, 5, tzinfo=UTC)

    with psycopg.connect(db, autocommit=True) as conn:
        store = OpenMeteoEventRepository(conn)
        first = ingest(parse_forecast(RESPONSE, "t1", "f1", fetched), store, publisher)
        again = ingest(
            parse_forecast(RESPONSE, "t1", "f1", fetched + timedelta(minutes=40)), store, publisher
        )
        rows = conn.execute(
            "SELECT id, idempotency_key, occurred_at, payload FROM raw.open_meteo_events ORDER BY occurred_at"
        ).fetchall()

    assert (len(first), again) == (2, [])
    assert [r[1] for r in rows] == [
        "weather:t1:f1:2026-11-25T12:00Z:2026-11-25T12:00Z",
        "weather:t1:f1:2026-11-25T13:00Z:2026-11-25T12:00Z",
    ]
    assert rows[1][2] == datetime(2026, 11, 25, 13, 0, tzinfo=UTC)
    assert rows[1][3]["hourly"] == {"time": "2026-11-25T13:00", "wind_speed_10m": 7.9}
    got = sqs.receive_message(QueueUrl=queue_url, MaxNumberOfMessages=10, WaitTimeSeconds=1)
    event_ids = sorted(json.loads(m["Body"])["event_id"] for m in got.get("Messages", []))
    assert event_ids == sorted(str(r[0]) for r in rows)
