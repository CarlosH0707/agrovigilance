"""Cliente da Open-Meteo: busca a previsão horária e a quebra em uma leitura por hora."""

import json
import os
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlencode
from urllib.request import urlopen

from agrovigilance.domain.weather_reading import WeatherReading

DEFAULT_URL = "https://api.open-meteo.com/v1/forecast"
# Fica no código, e não no env: as regras de alerta dependem exatamente dessas variáveis.
HOURLY = ("temperature_2m", "relative_humidity_2m", "precipitation_probability", "wind_speed_10m")


def fetch_forecast(latitude: float, longitude: float, forecast_days: int = 2) -> dict[str, Any]:
    query = urlencode(
        {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": ",".join(HOURLY),
            "timezone": "UTC",  # horários sem sufixo, mas em UTC
            "forecast_days": forecast_days,
        }
    )
    url = os.environ.get("OPEN_METEO_URL", DEFAULT_URL)  # ex.: endpoint pago ou um mock
    with urlopen(f"{url}?{query}", timeout=10) as response:
        return json.load(response)


def parse_forecast(
    response: dict[str, Any], tenant_id: str, field_id: str, fetched_at: datetime
) -> list[WeatherReading]:
    """Uma leitura por hora; o payload é a resposta como veio, com `hourly` recortado na hora."""
    if response.get("utc_offset_seconds", 0) != 0:
        raise ValueError("esperava a resposta em UTC (timezone=UTC)")
    hourly = response["hourly"]
    meta = {k: v for k, v in response.items() if k != "hourly"}
    readings = []
    for i, time in enumerate(hourly["time"]):
        hour = {name: values[i] for name, values in hourly.items()}
        readings.append(
            WeatherReading(
                tenant_id=tenant_id,
                field_id=field_id,
                target_hour=datetime.fromisoformat(time).replace(tzinfo=UTC),
                fetched_at=fetched_at,
                payload={**meta, "hourly": hour},
            )
        )
    return readings
