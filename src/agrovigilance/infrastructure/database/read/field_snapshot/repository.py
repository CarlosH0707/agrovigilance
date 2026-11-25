"""Repositório de read.field_snapshot; o SQL fica em queries/, um arquivo por query."""

from pathlib import Path

import psycopg

QUERIES = Path(__file__).parent / "queries"
REFRESH = (QUERIES / "refresh.sql").read_text(encoding="utf-8")


class FieldSnapshotRepository:
    def __init__(self, conn: psycopg.Connection):
        self.conn = conn

    def refresh(self, tenant_id: str, field_id: str) -> None:
        self.conn.execute(REFRESH, {"tenant_id": tenant_id, "field_id": field_id})
