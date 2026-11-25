"""Repositório de raw.field_events; o SQL fica em queries/, um arquivo por query."""

from pathlib import Path
from typing import Any
from uuid import UUID

import psycopg
from psycopg.types.json import Jsonb

from agrovigilance.domain.field_event import FieldEvent

QUERIES = Path(__file__).parent / "queries"
INSERT = (QUERIES / "insert.sql").read_text(encoding="utf-8")


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
