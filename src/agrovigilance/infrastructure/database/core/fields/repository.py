"""Repositório de core.fields; o SQL fica em queries/, um arquivo por query."""

from dataclasses import replace
from pathlib import Path
from uuid import UUID
from zoneinfo import ZoneInfo

import psycopg
from psycopg.rows import class_row

from agrovigilance.domain.field import Field

QUERIES = Path(__file__).parent / "queries"
LIST_ALL = (QUERIES / "list_all.sql").read_text(encoding="utf-8")
EXISTS = (QUERIES / "exists.sql").read_text(encoding="utf-8")


class FieldRepository:
    def __init__(self, conn: psycopg.Connection):
        self.conn = conn

    def list_all(self) -> list[Field]:
        with self.conn.cursor(row_factory=class_row(Field)) as cur:
            rows = cur.execute(LIST_ALL).fetchall()
        # O banco devolve o nome do fuso; o domínio trabalha com ZoneInfo.
        return [replace(row, timezone=ZoneInfo(row.timezone)) for row in rows]

    def exists(self, tenant_id: str, field_id: str) -> bool:
        try:
            producer_id = UUID(tenant_id)
        except ValueError:  # tenant que nem é UUID não está no cadastro
            return False
        params = {"producer_id": producer_id, "field_id": field_id}
        return self.conn.execute(EXISTS, params).fetchone()[0]
