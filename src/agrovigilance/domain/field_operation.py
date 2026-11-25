"""Apontamento de campo no formato canônico, com a lista fechada de tipos (ADR-0019)."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import AwareDatetime, TypeAdapter, ValidationError


class OperationType(StrEnum):
    SPRAYING_SCHEDULED = "pulverizacao_agendada"
    SPRAYING_DONE = "pulverizacao_concluida"


class InvalidFieldOperation(ValueError):
    """Dado inválido, não falha transitória: o worker marca `rejected` em vez de tentar de novo."""


@dataclass(frozen=True)
class FieldOperation:
    raw_event_id: UUID
    tenant_id: str
    field_id: str
    type: OperationType
    occurred_at: datetime  # quando o apontamento foi feito
    scheduled_for: datetime | None  # quando a pulverização agendada vai acontecer


_aware = TypeAdapter(AwareDatetime)


def from_raw(
    raw_event_id: UUID,
    tenant_id: str,
    field_id: str,
    occurred_at: datetime,
    payload: dict[str, Any],
) -> FieldOperation:
    """Converte uma linha de raw.field_events; levanta `InvalidFieldOperation` se não couber."""
    try:
        type_ = OperationType(payload.get("type"))
    except ValueError:
        raise InvalidFieldOperation(f"tipo fora da lista: {payload.get('type')!r}") from None

    scheduled_for = None
    if type_ is OperationType.SPRAYING_SCHEDULED:
        try:
            scheduled_for = _aware.validate_python(payload.get("scheduled_for"))
        except ValidationError:
            raise InvalidFieldOperation("agendamento sem scheduled_for com fuso") from None

    return FieldOperation(
        raw_event_id=raw_event_id,
        tenant_id=tenant_id,
        field_id=field_id,
        type=type_,
        occurred_at=occurred_at,
        scheduled_for=scheduled_for,
    )
