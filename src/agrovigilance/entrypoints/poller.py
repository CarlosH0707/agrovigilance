"""Coleta a previsão da Open-Meteo para cada talhão cadastrado, uma vez por execução.

Os talhões vêm de core.fields (ADR-0026); cada um vira uma linha por hora prevista (ADR-0018).
Uso: uv run --env-file .env python -m agrovigilance.entrypoints.poller
"""

import sys
from datetime import UTC, datetime

import boto3
import psycopg

from agrovigilance.application.ingest_weather import collect
from agrovigilance.domain.field import Field
from agrovigilance.domain.weather_reading import WeatherReading
from agrovigilance.infrastructure.database.connection import conninfo_from_env
from agrovigilance.infrastructure.database.core.fields.repository import FieldRepository
from agrovigilance.infrastructure.database.raw.open_meteo_events.repository import (
    OpenMeteoEventRepository,
)
from agrovigilance.infrastructure.open_meteo.client import fetch_forecast, parse_forecast
from agrovigilance.infrastructure.queues.events.publisher import QUEUE_NAME, EventsPublisher


def open_meteo(field: Field, fetched_at: datetime) -> list[WeatherReading]:
    response = fetch_forecast(field.latitude, field.longitude)
    return parse_forecast(response, field.producer_id, field.field_id, fetched_at)


def main() -> int:
    sqs = boto3.client("sqs")
    publisher = EventsPublisher(sqs, sqs.get_queue_url(QueueName=QUEUE_NAME)["QueueUrl"])
    with psycopg.connect(conninfo_from_env(), autocommit=True) as conn:
        fields = FieldRepository(conn).list_all()
        results = collect(
            fields, open_meteo, OpenMeteoEventRepository(conn), publisher, datetime.now(UTC)
        )
    if not fields:
        print("nenhum talhão cadastrado em core.fields")
    for (producer_id, field_id), result in results.items():
        if isinstance(result, Exception):
            print(f"{producer_id}/{field_id}: falhou: {result!r}", file=sys.stderr)
        else:
            print(f"{producer_id}/{field_id}: {len(result)} horas novas")
    return 1 if any(isinstance(r, Exception) for r in results.values()) else 0


if __name__ == "__main__":
    sys.exit(main())
