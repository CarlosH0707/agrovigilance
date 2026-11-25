from datetime import UTC, datetime

import pytest

from agrovigilance.infrastructure.open_meteo.client import parse_forecast

FETCHED = datetime(2026, 11, 25, 12, 0, tzinfo=UTC)
# Recorte de uma resposta real (coordenada genérica).
RESPONSE = {
    "latitude": -15.75,
    "longitude": -47.875,
    "generationtime_ms": 0.1,
    "utc_offset_seconds": 0,
    "timezone": "GMT",
    "timezone_abbreviation": "GMT",
    "elevation": 1061.0,
    "hourly_units": {"time": "iso8601", "wind_speed_10m": "km/h"},
    "hourly": {
        "time": ["2026-11-25T00:00", "2026-11-25T01:00"],
        "wind_speed_10m": [5.2, 7.9],
    },
}


def test_one_reading_per_hour_with_utc_target_and_sliced_payload():
    first, second = parse_forecast(RESPONSE, "t1", "f1", FETCHED)

    assert first.target_hour == datetime(2026, 11, 25, 0, 0, tzinfo=UTC)
    assert second.target_hour == datetime(2026, 11, 25, 1, 0, tzinfo=UTC)
    assert (first.tenant_id, first.field_id, first.fetched_at) == ("t1", "f1", FETCHED)
    assert second.payload["hourly"] == {"time": "2026-11-25T01:00", "wind_speed_10m": 7.9}
    assert second.payload["hourly_units"] == RESPONSE["hourly_units"]
    assert second.payload["elevation"] == 1061.0


def test_non_utc_response_is_rejected():
    with pytest.raises(ValueError):
        parse_forecast({**RESPONSE, "utc_offset_seconds": -10800}, "t1", "f1", FETCHED)
