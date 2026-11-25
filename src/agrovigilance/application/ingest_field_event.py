"""Caso de uso: gravar o apontamento uma vez e publicar só se for novo (ADR-0002, ADR-0004)."""

from typing import Any, Protocol
from uuid import UUID

from agrovigilance.domain.field_event import FieldEvent, idempotency_key


class EventStore(Protocol):
    def insert(self, key: str, event: FieldEvent, payload: dict[str, Any]) -> UUID | None:
        """Grava e devolve o id; `None` se a chave já existia. Commita antes de voltar."""


class Publisher(Protocol):
    def publish(self, message: dict[str, Any]) -> None: ...


def ingest(
    event: FieldEvent, payload: dict[str, Any], store: EventStore, publisher: Publisher
) -> UUID | None:
    """Devolve o id do evento novo, ou `None` se for duplicata (nada é publicado)."""
    event_id = store.insert(idempotency_key(event), event, payload)
    if event_id is not None:
        # Mensagem fina: o worker lê o payload do banco.
        publisher.publish(
            {
                "source": "field_events",
                "event_id": str(event_id),
                "tenant_id": event.tenant_id,
                "field_id": event.field_id,
            }
        )
    return event_id
