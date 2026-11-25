from datetime import UTC, datetime
from uuid import uuid4

import pytest

from agrovigilance.domain.weather_forecast import from_raw

FETCHED = datetime(2026, 11, 25, 12, 0, 5, tzinfo=UTC)


def payload(**overrides):
    # Formato que o client grava no raw: metadados + `hourly` recortado em uma hora.
    base = {
        "utc_offset_seconds": 0,
        "hourly_units": {
            "time": "iso8601",
            "temperature_2m": "°C",
            "relative_humidity_2m": "%",
            "precipitation_probability": "%",
            "wind_speed_10m": "km/h",
        },
        "hourly": {
            "time": "2026-11-26T15:00",
            "temperature_2m": 28.4,
            "relative_humidity_2m": 61,
            "precipitation_probability": 10,
            "wind_speed_10m": 7.2,
        },
    }
    return {**base, **overrides}


def test_converts_raw_hour_to_typed_forecast_in_utc():
    raw_id = uuid4()
    forecast = from_raw(raw_id, "t1", "f1", FETCHED, payload())

    assert forecast.raw_event_id == raw_id
    assert forecast.target_hour == datetime(2026, 11, 26, 15, tzinfo=UTC)
    assert forecast.fetched_at == FETCHED
    assert forecast.temperature_c == 28.4
    assert forecast.relative_humidity_pct == 61
    assert forecast.precipitation_probability_pct == 10
    assert forecast.wind_speed_kmh == 7.2


def test_missing_value_stays_null():
    hour = {**payload()["hourly"], "wind_speed_10m": None}
    assert from_raw(uuid4(), "t1", "f1", FETCHED, payload(hourly=hour)).wind_speed_kmh is None


def test_refuses_non_utc_payload():
    with pytest.raises(ValueError, match="UTC"):
        from_raw(uuid4(), "t1", "f1", FETCHED, payload(utc_offset_seconds=-10800))


def test_refuses_unexpected_unit():
    units = {**payload()["hourly_units"], "wind_speed_10m": "m/s"}
    with pytest.raises(ValueError, match="wind_speed_10m"):
        from_raw(uuid4(), "t1", "f1", FETCHED, payload(hourly_units=units))
