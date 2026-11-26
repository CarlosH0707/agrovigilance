"""Repositório de core.fields; o SQL fica em queries/, um arquivo por query."""

from dataclasses import replace
from pathlib import Path
from zoneinfo import ZoneInfo

import psycopg
from psycopg.rows import class_row

from agrovigilance.domain.field import Field

QUERIES = Path(__file__).parent / "queries"
LIST_ALL = (QUERIES / "list_all.sql").read_text(encoding="utf-8")


class FieldRepository:
    def __init__(self, conn: psycopg.Connection):
        self.conn = conn

    def list_all(self) -> list[Field]:
        with self.conn.cursor(row_factory=class_row(Field)) as cur:
            rows = cur.execute(LIST_ALL).fetchall()
        # O banco devolve o nome do fuso; o domínio trabalha com ZoneInfo.
        return [replace(row, timezone=ZoneInfo(row.timezone)) for row in rows]
