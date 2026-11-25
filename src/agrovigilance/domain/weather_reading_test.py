from datetime import UTC, datetime, timedelta, timezone

import pytest

from agrovigilance.domain.weather_reading import WeatherReading, idempotency_key

TARGET = datetime(2026, 11, 26, 15, 0, tzinfo=UTC)
FETCHED = datetime(2026, 11, 25, 12, 34, 56, tzinfo=UTC)


def reading(**overrides):
    base = {
        "tenant_id": "t1",
        "field_id": "f1",
        "target_hour": TARGET,
        "fetched_at": FETCHED,
        "payload": {},
    }
    return WeatherReading(**{**base, **overrides})


def test_key_has_target_hour_and_fetch_bucket_in_utc():
    assert idempotency_key(reading()) == "weather:t1:f1:2026-11-26T15:00Z:2026-11-25T12:00Z"


def test_same_fetch_hour_gives_same_key_even_in_other_timezone():
    brt = timezone(timedelta(hours=-3))
    later_same_hour = reading(fetched_at=datetime(2026, 11, 25, 9, 59, tzinfo=brt))
    assert idempotency_key(later_same_hour) == idempotency_key(reading())


@pytest.mark.parametrize(
    "change",
    [
        {"fetched_at": FETCHED + timedelta(hours=1)},  # previsão nova = nova versão
        {"target_hour": TARGET + timedelta(hours=1)},
        {"field_id": "f2"},
        {"tenant_id": "t2"},
    ],
)
def test_key_changes_with_identifying_fields(change):
    assert idempotency_key(reading(**change)) != idempotency_key(reading())


def test_naive_datetime_is_rejected():
    with pytest.raises(ValueError):
        reading(target_hour=datetime(2026, 11, 26, 15, 0))
