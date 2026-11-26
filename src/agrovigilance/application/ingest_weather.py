"""Caso de uso: gravar cada hora da previsão uma vez e publicar só as novas (ADR-0002, ADR-0004)."""

from collections.abc import Iterable
from datetime import datetime
from typing import Protocol
from uuid import UUID

from agrovigilance.application.ingest_field_event import Publisher
from agrovigilance.domain.field import Field
from agrovigilance.domain.weather_reading import WeatherReading, idempotency_key


class WeatherStore(Protocol):
    def insert(self, key: str, reading: WeatherReading) -> UUID | None:
        """Grava e devolve o id; `None` se a chave já existia. Commita antes de voltar."""


def ingest(
    readings: Iterable[WeatherReading], store: WeatherStore, publisher: Publisher
) -> list[UUID]:
    """Devolve os ids das horas novas; duplicatas não são publicadas."""
    new_ids = []
    for reading in readings:
        event_id = store.insert(idempotency_key(reading), reading)
        if event_id is None:
            continue
        publisher.publish(
            {
                "source": "open_meteo_events",
                "event_id": str(event_id),
                "tenant_id": reading.tenant_id,
                "field_id": reading.field_id,
            }
        )
        new_ids.append(event_id)
    return new_ids


class ForecastSource(Protocol):
    def __call__(self, field: Field, fetched_at: datetime) -> list[WeatherReading]:
        """Busca a previsão do talhão e quebra em uma leitura por hora."""


def collect(
    fields: Iterable[Field],
    source: ForecastSource,
    store: WeatherStore,
    publisher: Publisher,
    fetched_at: datetime,
) -> dict[tuple[str, str], list[UUID] | Exception]:
    """Uma coleta por talhão (ADR-0026). A falha de um talhão não impede os outros."""
    results: dict[tuple[str, str], list[UUID] | Exception] = {}
    for field in fields:
        key = (field.producer_id, field.field_id)
        try:
            results[key] = ingest(source(field, fetched_at), store, publisher)
        except Exception as error:  # noqa: BLE001 — um talhão com problema não para os outros
            results[key] = error
    return results
