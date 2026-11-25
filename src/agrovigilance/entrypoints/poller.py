"""Coleta a previsão da Open-Meteo para o talhão fixo do .env, uma vez por execução (ADR-0018).

Uso: uv run --env-file .env python -m agrovigilance.entrypoints.poller
"""

import os
from datetime import UTC, datetime

import boto3
import psycopg

from agrovigilance.application.ingest_weather import ingest
from agrovigilance.infrastructure.database.connection import conninfo_from_env
from agrovigilance.infrastructure.database.raw.open_meteo_events.repository import (
    OpenMeteoEventRepository,
)
from agrovigilance.infrastructure.open_meteo.client import fetch_forecast, parse_forecast
from agrovigilance.infrastructure.queues.events.publisher import QUEUE_NAME, EventsPublisher


def main() -> None:
    response = fetch_forecast(float(os.environ["FIELD_LAT"]), float(os.environ["FIELD_LON"]))
    readings = parse_forecast(
        response, os.environ["FIELD_TENANT_ID"], os.environ["FIELD_ID"], datetime.now(UTC)
    )
    sqs = boto3.client("sqs")
    publisher = EventsPublisher(sqs, sqs.get_queue_url(QueueName=QUEUE_NAME)["QueueUrl"])
    with psycopg.connect(conninfo_from_env(), autocommit=True) as conn:
        new_ids = ingest(readings, OpenMeteoEventRepository(conn), publisher)
    print(f"{len(readings)} horas lidas, {len(new_ids)} novas")


if __name__ == "__main__":
    main()
