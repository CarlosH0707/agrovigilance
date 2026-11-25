"""Caso de uso: gravar cada hora da previsão uma vez e publicar só as novas (ADR-0002, ADR-0004)."""

from collections.abc import Iterable
from typing import Protocol
from uuid import UUID

from agrovigilance.application.ingest_field_event import Publisher
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
