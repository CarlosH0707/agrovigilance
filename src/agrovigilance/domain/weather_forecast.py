"""Uma hora de previsão no formato canônico (ADR-0019)."""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

# Unidades que as colunas assumem. Outra unidade é bug na ingestão, não dado a converter.
EXPECTED_UNITS = {
    "temperature_2m": "°C",
    "relative_humidity_2m": "%",
    "precipitation_probability": "%",
    "wind_speed_10m": "km/h",
}


@dataclass(frozen=True)
class WeatherForecast:
    raw_event_id: UUID
    tenant_id: str
    field_id: str
    target_hour: datetime
    fetched_at: datetime
    temperature_c: float | None  # a API pode não ter a hora: nulo, não zero
    relative_humidity_pct: float | None
    precipitation_probability_pct: float | None
    wind_speed_kmh: float | None


def from_raw(
    raw_event_id: UUID, tenant_id: str, field_id: str, fetched_at: datetime, payload: dict[str, Any]
) -> WeatherForecast:
    """Converte uma linha de raw.open_meteo_events; `fetched_at` é o `ingested_at` dela."""
    if payload.get("utc_offset_seconds") != 0:
        raise ValueError("esperava a previsão em UTC")
    units = payload.get("hourly_units", {})
    for name, unit in EXPECTED_UNITS.items():
        if units.get(name) != unit:
            raise ValueError(f"unidade inesperada para {name}: {units.get(name)!r}")
    hour = payload["hourly"]
    return WeatherForecast(
        raw_event_id=raw_event_id,
        tenant_id=tenant_id,
        field_id=field_id,
        target_hour=datetime.fromisoformat(hour["time"]).replace(tzinfo=UTC),
        fetched_at=fetched_at,
        temperature_c=hour["temperature_2m"],
        relative_humidity_pct=hour["relative_humidity_2m"],
        precipitation_probability_pct=hour["precipitation_probability"],
        wind_speed_kmh=hour["wind_speed_10m"],
    )
