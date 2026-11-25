"""Uma hora de previsão da Open-Meteo para um talhão (ADR-0002, ADR-0018)."""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True)
class WeatherReading:
    tenant_id: str
    field_id: str
    target_hour: datetime  # hora prevista
    fetched_at: datetime  # quando coletamos; define a versão da previsão
    payload: dict[str, Any]  # a hora como veio da API

    def __post_init__(self):
        # Sem fuso, a chave dependeria do relógio da máquina.
        if self.target_hour.tzinfo is None or self.fetched_at.tzinfo is None:
            raise ValueError("target_hour e fetched_at precisam de fuso")


def _hour(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:00Z")


def idempotency_key(reading: WeatherReading) -> str:
    """`weather:{tenant}:{field}:{target_hour}:{bucket}`; bucket = hora da coleta em UTC."""
    return ":".join(
        [
            "weather",
            reading.tenant_id,
            reading.field_id,
            _hour(reading.target_hour),
            _hour(reading.fetched_at),
        ]
    )
