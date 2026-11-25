"""Mesmo apontamento enviado 2x → 1 linha no raw e 1 mensagem na fila (critério da Fase 1)."""

import json
import uuid

import psycopg
import pytest
from fastapi.testclient import TestClient

from agrovigilance.entrypoints.api import app, get_publisher, get_store
from agrovigilance.infrastructure.database.raw.field_events.repository import FieldEventRepository
from agrovigilance.infrastructure.queues.events.publisher import EventsPublisher
from scripts.create_queues import ensure_queues
from scripts.migrate import migrate

pytestmark = pytest.mark.integration


def test_duplicate_post_stores_once_and_publishes_once(db, sqs):
    migrate(db)
    suffix = uuid.uuid4().hex[:8]
    queue_url = ensure_queues(sqs, f"events-{suffix}", f"events-{suffix}-dlq")
    event = {
        "tenant_id": "t1",
        "field_id": "f1",
        "type": "spray_scheduled",
        "occurred_at": "2026-11-25T10:00:00-03:00",
        "source_event_id": "app-123",
    }

    with psycopg.connect(db, autocommit=True) as conn:
        app.dependency_overrides = {
            get_store: lambda: FieldEventRepository(conn),
            get_publisher: lambda: EventsPublisher(sqs, queue_url),
        }
        try:
            http = TestClient(app)
            first = http.post("/webhooks/field", json=event)
            again = http.post("/webhooks/field", json=event)
        finally:
            app.dependency_overrides = {}

        rows = conn.execute("SELECT id, idempotency_key, payload FROM raw.field_events").fetchall()

    assert (first.status_code, again.status_code) == (202, 200)
    [(row_id, key, payload)] = rows
    assert key == "field_event:app-123"
    assert payload == event
    got = sqs.receive_message(QueueUrl=queue_url, MaxNumberOfMessages=10, WaitTimeSeconds=1)
    bodies = [json.loads(m["Body"]) for m in got.get("Messages", [])]
    assert bodies == [
        {"source": "field_events", "event_id": str(row_id), "tenant_id": "t1", "field_id": "f1"}
    ]
    assert first.json()["event_id"] == str(row_id)
