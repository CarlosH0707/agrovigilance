import uuid
from datetime import UTC, datetime, timedelta

from agrovigilance.application.ingest_weather import ingest
from agrovigilance.domain.weather_reading import WeatherReading

FETCHED = datetime(2026, 11, 25, 12, 0, tzinfo=UTC)


def readings(fetched_at=FETCHED, hours=3):
    start = datetime(2026, 11, 25, 12, 0, tzinfo=UTC)
    return [
        WeatherReading("t1", "f1", start + timedelta(hours=h), fetched_at, {"h": h})
        for h in range(hours)
    ]


class FakeStore:
    def __init__(self):
        self.rows = {}

    def insert(self, key, reading):
        if key in self.rows:
            return None
        self.rows[key] = uuid.uuid4()
        return self.rows[key]


class FakePublisher:
    def __init__(self):
        self.messages = []

    def publish(self, message):
        self.messages.append(message)


def test_each_new_hour_is_stored_and_published():
    store, publisher = FakeStore(), FakePublisher()

    new_ids = ingest(readings(), store, publisher)

    assert len(new_ids) == 3
    assert publisher.messages == [
        {"source": "open_meteo_events", "event_id": str(i), "tenant_id": "t1", "field_id": "f1"}
        for i in new_ids
    ]


def test_same_fetch_hour_twice_publishes_nothing_new():
    store, publisher = FakeStore(), FakePublisher()
    ingest(readings(), store, publisher)

    assert ingest(readings(fetched_at=FETCHED + timedelta(minutes=30)), store, publisher) == []
    assert len(store.rows) == 3
    assert len(publisher.messages) == 3


def test_next_fetch_hour_is_a_new_version():
    store, publisher = FakeStore(), FakePublisher()
    ingest(readings(), store, publisher)

    assert len(ingest(readings(fetched_at=FETCHED + timedelta(hours=1)), store, publisher)) == 3
    assert len(publisher.messages) == 6
