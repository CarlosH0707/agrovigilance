"""Uma linha de raw.<fonte>_events como o worker a lê (ADR-0019)."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class RawEvent:
    id: UUID
    tenant_id: str
    field_id: str
    occurred_at: datetime
    ingested_at: datetime
    payload: dict[str, Any]
