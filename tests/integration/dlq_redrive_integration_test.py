"""Banco fora → 3 falhas → DLQ → banco volta → redrive → processado (ADR-0021, ADR-0023)."""

import uuid

import psycopg
import pytest
from psycopg.conninfo import conninfo_to_dict, make_conninfo

from agrovigilance.application import ingest_field_event
from agrovigilance.domain.field_event import FieldEvent
from agrovigilance.entrypoints.worker import process_once
from agrovigilance.infrastructure.database.raw.field_events.repository import FieldEventRepository
from agrovigilance.infrastructure.queues.events.consumer import EventsConsumer
from agrovigilance.infrastructure.queues.events.publisher import EventsPublisher
from scripts.create_queues import MAX_RECEIVE_COUNT, ensure_queues
from scripts.migrate import migrate
from scripts.redrive_dlq import redrive

pytestmark = pytest.mark.integration


def test_failed_message_goes_to_dlq_and_redrive_brings_it_back(db, sqs):
    suffix = uuid.uuid4().hex[:8]
    queue, dlq = f"events-{suffix}", f"events-{suffix}-dlq"
    queue_url = ensure_queues(sqs, queue, dlq)
    # Visibilidade zero: a mensagem que falhou volta na hora, sem esperar 30 s.
    sqs.set_queue_attributes(QueueUrl=queue_url, Attributes={"VisibilityTimeout": "0"})
    migrate(db)
    body = {
        "tenant_id": "t1",
        "field_id": "f1",
        "type": "pulverizacao_concluida",
        "occurred_at": "2026-11-25T10:00:00-03:00",
        "source_event_id": uuid.uuid4().hex,
    }
    with psycopg.connect(db, autocommit=True) as conn:
        event_id = ingest_field_event.ingest(
            FieldEvent.model_validate(body),
            body,
            FieldEventRepository(conn),
            EventsPublisher(sqs, queue_url),
        )

    consumer = EventsConsumer(sqs, queue_url, wait_seconds=1)
    db_down = make_conninfo(**{**conninfo_to_dict(db), "dbname": "nao_existe"})
    for _ in range(MAX_RECEIVE_COUNT):
        with pytest.raises(psycopg.OperationalError):
            process_once(consumer, db_down)

    assert process_once(consumer, db) == 0  # a fila principal ficou vazia
    dlq_url = sqs.get_queue_url(QueueName=dlq)["QueueUrl"]
    depth = sqs.get_queue_attributes(
        QueueUrl=dlq_url, AttributeNames=["ApproximateNumberOfMessages"]
    )["Attributes"]["ApproximateNumberOfMessages"]
    assert depth == "1"

    assert redrive(sqs, dlq) == 1
    assert process_once(consumer, db) == 1

    with psycopg.connect(db) as conn:
        status = conn.execute(
            "SELECT status FROM raw.field_events WHERE id = %s", (event_id,)
        ).fetchone()
        operations = conn.execute("SELECT count(*) FROM core.field_operations").fetchone()
    assert status == ("processed",)
    assert operations == (1,)
