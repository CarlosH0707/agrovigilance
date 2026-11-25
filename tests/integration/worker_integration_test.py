"""Worker de ponta a ponta: raw → fila → core, com reentrega e evento inválido (ADR-0021)."""

import json
import uuid
from datetime import UTC, datetime

import psycopg
import pytest

from agrovigilance.application import ingest_field_event, ingest_weather
from agrovigilance.domain.field_event import FieldEvent
from agrovigilance.domain.weather_reading import WeatherReading
from agrovigilance.entrypoints.worker import process_once
from agrovigilance.infrastructure.database.raw.field_events.repository import FieldEventRepository
from agrovigilance.infrastructure.database.raw.open_meteo_events.repository import (
    OpenMeteoEventRepository,
)
from agrovigilance.infrastructure.queues.events.consumer import EventsConsumer
from agrovigilance.infrastructure.queues.events.publisher import EventsPublisher
from scripts.create_queues import ensure_queues
from scripts.migrate import migrate

pytestmark = pytest.mark.integration

WEATHER = {
    "utc_offset_seconds": 0,
    "hourly_units": {
        "temperature_2m": "°C",
        "relative_humidity_2m": "%",
        "precipitation_probability": "%",
        "wind_speed_10m": "km/h",
    },
    "hourly": {
        "time": "2026-11-26T15:00",
        "temperature_2m": 28.4,
        "relative_humidity_2m": 61,
        "precipitation_probability": 10,
        "wind_speed_10m": 7.2,
    },
}


def field_event(type_, **extra):
    body = {"tenant_id": "t1", "field_id": "f1", "type": type_, **extra}
    body["occurred_at"] = "2026-11-25T10:00:00-03:00"
    body["source_event_id"] = uuid.uuid4().hex
    return FieldEvent.model_validate(body), body


@pytest.fixture
def queue_url(sqs):
    suffix = uuid.uuid4().hex[:8]
    return ensure_queues(sqs, f"events-{suffix}", f"events-{suffix}-dlq")


def test_worker_fills_core_and_marks_raw(db, sqs, queue_url):
    migrate(db)
    publisher = EventsPublisher(sqs, queue_url)
    with psycopg.connect(db, autocommit=True) as conn:
        [weather_id] = ingest_weather.ingest(
            [
                WeatherReading(
                    "t1",
                    "f1",
                    datetime(2026, 11, 26, 15, tzinfo=UTC),
                    datetime.now(UTC),
                    WEATHER,
                )
            ],
            OpenMeteoEventRepository(conn),
            publisher,
        )
        scheduled_id = ingest_field_event.ingest(
            *field_event("pulverizacao_agendada", scheduled_for="2026-11-26T07:00:00-03:00"),
            FieldEventRepository(conn),
            publisher,
        )
        rejected_id = ingest_field_event.ingest(
            *field_event("colheita"), FieldEventRepository(conn), publisher
        )
    # A SQS Standard pode entregar duas vezes: simula a reentrega do agendamento.
    publisher.publish({"source": "field_events", "event_id": str(scheduled_id)})

    consumer = EventsConsumer(sqs, queue_url, wait_seconds=1)
    done = 0
    for _ in range(5):  # o Floci pode devolver as 4 mensagens em mais de um receive
        done += process_once(consumer, db)
    assert done == 4

    with psycopg.connect(db) as conn:
        forecast = conn.execute(
            "SELECT raw_event_id, wind_speed_kmh FROM core.weather_forecasts"
        ).fetchall()
        operations = conn.execute(
            "SELECT raw_event_id, type, scheduled_for FROM core.field_operations"
        ).fetchall()
        statuses = dict(
            conn.execute(
                "SELECT id, status FROM raw.field_events"
                " UNION ALL SELECT id, status FROM raw.open_meteo_events"
            ).fetchall()
        )

    assert forecast == [(weather_id, 7.2)]
    assert operations == [
        (scheduled_id, "pulverizacao_agendada", datetime(2026, 11, 26, 10, tzinfo=UTC))
    ]
    assert statuses == {
        weather_id: "processed",
        scheduled_id: "processed",
        rejected_id: "rejected",
    }
    leftover = sqs.receive_message(QueueUrl=queue_url, WaitTimeSeconds=1).get("Messages", [])
    assert [json.loads(m["Body"]) for m in leftover] == []
