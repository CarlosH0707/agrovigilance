"""Repositório de raw.open_meteo_events; o SQL fica em queries/, um arquivo por query."""

from pathlib import Path
from uuid import UUID

import psycopg
from psycopg.types.json import Jsonb

from agrovigilance.domain.weather_reading import WeatherReading

QUERIES = Path(__file__).parent / "queries"
INSERT = (QUERIES / "insert.sql").read_text(encoding="utf-8")


class OpenMeteoEventRepository:
    def __init__(self, conn: psycopg.Connection):
        self.conn = conn

    def insert(self, key: str, reading: WeatherReading) -> UUID | None:
        # transaction() commita ao sair: o publish só acontece depois disso (ADR-0004).
        with self.conn.transaction():
            row = self.conn.execute(
                INSERT,
                {
                    "idempotency_key": key,
                    "tenant_id": reading.tenant_id,
                    "field_id": reading.field_id,
                    "occurred_at": reading.target_hour,  # o fato é a hora prevista
                    "payload": Jsonb(reading.payload),
                },
            ).fetchone()
        return row[0] if row else None
