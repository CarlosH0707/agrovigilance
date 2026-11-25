"""Repositório de raw.field_events; o SQL fica em queries/, um arquivo por query."""

from pathlib import Path
from typing import Any
from uuid import UUID

import psycopg
from psycopg.types.json import Jsonb

from agrovigilance.domain.field_event import FieldEvent
from agrovigilance.domain.raw_event import RawEvent

QUERIES = Path(__file__).parent / "queries"
INSERT = (QUERIES / "insert.sql").read_text(encoding="utf-8")
GET = (QUERIES / "get.sql").read_text(encoding="utf-8")
SET_STATUS = (QUERIES / "set_status.sql").read_text(encoding="utf-8")


class FieldEventRepository:
    def __init__(self, conn: psycopg.Connection):
        self.conn = conn

    def insert(self, key: str, event: FieldEvent, payload: dict[str, Any]) -> UUID | None:
        # transaction() commita ao sair: o publish só acontece depois disso (ADR-0004).
        with self.conn.transaction():
            row = self.conn.execute(
                INSERT,
                {
                    "idempotency_key": key,
                    "tenant_id": event.tenant_id,
                    "field_id": event.field_id,
                    "occurred_at": event.occurred_at,
                    "payload": Jsonb(payload),
                },
            ).fetchone()
        return row[0] if row else None

    def get(self, event_id: UUID) -> RawEvent | None:
        row = self.conn.execute(GET, {"id": event_id}).fetchone()
        return RawEvent(*row) if row else None

    def set_status(self, event_id: UUID, status: str) -> None:
        self.conn.execute(SET_STATUS, {"id": event_id, "status": status})
