"""API HTTP: recebe apontamentos de campo (ADR-0016).

Uso: uv run --env-file .env uvicorn agrovigilance.entrypoints.api:app
"""

from functools import cache
from typing import Any

import boto3
import psycopg
from fastapi import Body, Depends, FastAPI, Response, status
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from agrovigilance.application.ingest_field_event import EventStore, Publisher, ingest
from agrovigilance.domain.field_event import FieldEvent
from agrovigilance.infrastructure.database.connection import conninfo_from_env
from agrovigilance.infrastructure.database.raw.field_events.repository import FieldEventRepository
from agrovigilance.infrastructure.queues.events.publisher import QUEUE_NAME, EventsPublisher

app = FastAPI(title="AgroVigilance")


def get_store():
    with psycopg.connect(conninfo_from_env(), autocommit=True) as conn:
        yield FieldEventRepository(conn)


@cache
def get_publisher() -> Publisher:
    sqs = boto3.client("sqs")
    return EventsPublisher(sqs, sqs.get_queue_url(QueueName=QUEUE_NAME)["QueueUrl"])


@app.post("/webhooks/field", status_code=status.HTTP_202_ACCEPTED)
def receive_field_event(
    response: Response,
    payload: dict[str, Any] = Body(...),
    store: EventStore = Depends(get_store),
    publisher: Publisher = Depends(get_publisher),
):
    # Valida aqui (e não na assinatura) para gravar o corpo exatamente como chegou.
    try:
        event = FieldEvent.model_validate(payload)
    except ValidationError as e:
        raise RequestValidationError(e.errors(include_url=False)) from e
    event_id = ingest(event, payload, store, publisher)
    if event_id is None:
        response.status_code = status.HTTP_200_OK
        return {"status": "duplicate"}
    return {"status": "accepted", "event_id": str(event_id)}
