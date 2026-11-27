"""Apontamento de campo no formato canônico, com a lista fechada de tipos (ADR-0019, ADR-0027)."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import AwareDatetime, TypeAdapter, ValidationError

from agrovigilance.domain import products
from agrovigilance.domain.products import ProductClass


class OperationType(StrEnum):
    SPRAYING_SCHEDULED = "pulverizacao_agendada"
    SPRAYING_DONE = "pulverizacao_concluida"


class Equipment(StrEnum):
    TRACTOR = "trator"
    DRONE = "drone"
    BACKPACK = "costal"


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
    product: str | None = None  # id do catálogo; produto desconhecido fica como veio
    product_class: ProductClass | None = None
    equipment: Equipment | None = None  # sem equipamento, o alerta pergunta: nunca assume


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

    product, product_class = _product(payload)
    return FieldOperation(
        raw_event_id=raw_event_id,
        tenant_id=tenant_id,
        field_id=field_id,
        type=type_,
        occurred_at=occurred_at,
        scheduled_for=scheduled_for,
        product=product,
        product_class=product_class,
        equipment=_closed(Equipment, payload.get("equipment"), "equipamento"),
    )


def _closed[E: StrEnum](enum: type[E], value: Any, label: str) -> E | None:
    """Valor de lista fechada: ausente vira None; fora da lista é apontamento inválido."""
    if value is None:
        return None
    try:
        return enum(value)
    except ValueError, TypeError:  # TypeError: lista ou dict no lugar do texto
        raise InvalidFieldOperation(f"{label} fora da lista: {value!r}") from None


def _product(payload: dict[str, Any]) -> tuple[str | None, ProductClass | None]:
    """Produto do catálogo vira id e classe; desconhecido fica como veio, com a classe informada."""
    product_class = _closed(ProductClass, payload.get("product_class"), "classe de produto")
    text = payload.get("product")
    if text is None:
        return None, product_class
    if not isinstance(text, str) or not text.strip():
        raise InvalidFieldOperation(f"produto inválido: {text!r}")
    known = products.find(text)
    if known is None:
        return text.strip(), product_class
    if product_class is not None and product_class is not known.product_class:
        raise InvalidFieldOperation(f"{known.name} é {known.product_class}, não {product_class}")
    return known.id, known.product_class
