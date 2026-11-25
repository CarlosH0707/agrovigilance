"""Repositório de core.field_operations; o SQL fica em queries/, um arquivo por query."""

from dataclasses import asdict
from pathlib import Path

import psycopg

from agrovigilance.domain.field_operation import FieldOperation

QUERIES = Path(__file__).parent / "queries"
INSERT = (QUERIES / "insert.sql").read_text(encoding="utf-8")


class FieldOperationRepository:
    def __init__(self, conn: psycopg.Connection):
        self.conn = conn

    def insert(self, item: FieldOperation) -> None:
        self.conn.execute(INSERT, asdict(item))
