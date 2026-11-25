"""Caso de uso do worker: raw → canônico em core, uma mensagem por vez (ADR-0019, ADR-0021).

Idempotente sem transação entre tabelas: se cair entre gravar o core e marcar o raw,
a mensagem volta, o INSERT no core não duplica (UNIQUE raw_event_id) e o status é marcado.
"""

from collections.abc import Callable, Mapping
from typing import Literal, Protocol
from uuid import UUID

from pydantic import BaseModel

from agrovigilance.domain import field_operation, weather_forecast
from agrovigilance.domain.raw_event import RawEvent


class EventMessage(BaseModel):
    """O que o worker precisa da mensagem fina; os outros campos são ignorados."""

    source: Literal["open_meteo_events", "field_events"]
    event_id: UUID


class RawEvents(Protocol):
    def get(self, event_id: UUID) -> RawEvent | None: ...
    def set_status(self, event_id: UUID, status: str) -> None: ...


class CanonicalStore[T](Protocol):
    def insert(self, item: T) -> None:
        """Grava uma vez por `raw_event_id`; repetir não faz nada."""


Handler = Callable[[UUID], str]


def handle(body: str, handlers: Mapping[str, Handler]) -> str:
    """Valida a mensagem e chama o handler da fonte; devolve o status gravado no raw."""
    message = EventMessage.model_validate_json(body)
    return handlers[message.source](message.event_id)


def _load(raw: RawEvents, event_id: UUID) -> RawEvent:
    row = raw.get(event_id)
    if row is None:
        # Mensagem publicada só após o commit (ADR-0004): sumir é bug, não dado inválido.
        raise LookupError(f"evento {event_id} não está no raw")
    return row


def process_weather(
    event_id: UUID, raw: RawEvents, core: CanonicalStore[weather_forecast.WeatherForecast]
) -> str:
    row = _load(raw, event_id)
    # Unidade ou fuso errado levanta ValueError: é bug na ingestão, então vai para a DLQ.
    core.insert(
        weather_forecast.from_raw(row.id, row.tenant_id, row.field_id, row.ingested_at, row.payload)
    )
    raw.set_status(event_id, "processed")
    return "processed"


def process_field_operation(
    event_id: UUID, raw: RawEvents, core: CanonicalStore[field_operation.FieldOperation]
) -> str:
    row = _load(raw, event_id)
    try:
        op = field_operation.from_raw(
            row.id, row.tenant_id, row.field_id, row.occurred_at, row.payload
        )
    except field_operation.InvalidFieldOperation:
        # Dado inválido não melhora tentando de novo: marca e segue, sem DLQ.
        raw.set_status(event_id, "rejected")
        return "rejected"
    core.insert(op)
    raw.set_status(event_id, "processed")
    return "processed"
