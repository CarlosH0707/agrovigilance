"""Apontamento de campo recebido pelo webhook (ADR-0002)."""

import hashlib
from datetime import UTC

from pydantic import AwareDatetime, BaseModel, ConfigDict


class FieldEvent(BaseModel):
    # Campos extras são aceitos: o payload bruto inteiro vai para o raw.
    model_config = ConfigDict(extra="allow")

    tenant_id: str
    field_id: str
    type: str  # texto livre na Fase 1; lista fechada vem com o canonical payload
    occurred_at: AwareDatetime  # sem fuso é rejeitado: o hash depende do instante exato
    source_event_id: str | None = None


def idempotency_key(event: FieldEvent) -> str:
    """`field_event:{source_event_id}`, ou hash dos campos que identificam o fato."""
    if event.source_event_id:
        return f"field_event:{event.source_event_id}"
    occurred = event.occurred_at.astimezone(UTC).isoformat()
    parts = "|".join([event.tenant_id, event.field_id, event.type, occurred])
    return f"field_event:{hashlib.sha256(parts.encode()).hexdigest()}"
