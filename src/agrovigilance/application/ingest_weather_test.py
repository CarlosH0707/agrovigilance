import uuid
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from agrovigilance.application.ingest_weather import collect, ingest
from agrovigilance.domain.field import Field
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


def field(field_id, producer_id="p1"):
    return Field(
        producer_id=producer_id,
        field_id=field_id,
        name=field_id,
        crop="cafe",
        area_ha=None,
        latitude=-19.0,
        longitude=-40.0,
        region="ES",
        timezone=ZoneInfo("America/Sao_Paulo"),
        temperature_tolerable_max_c=None,
    )


def test_collect_reads_each_field_with_its_own_ids():
    store, publisher = FakeStore(), FakePublisher()

    def source(f, fetched_at):
        start = datetime(2026, 11, 25, 12, 0, tzinfo=UTC)
        return [WeatherReading(f.producer_id, f.field_id, start, fetched_at, {})]

    results = collect([field("a"), field("b", "p2")], source, store, publisher, FETCHED)

    assert {k: len(v) for k, v in results.items()} == {("p1", "a"): 1, ("p2", "b"): 1}
    assert {(m["tenant_id"], m["field_id"]) for m in publisher.messages} == {
        ("p1", "a"),
        ("p2", "b"),
    }


def test_collect_keeps_going_when_one_field_fails():
    store, publisher = FakeStore(), FakePublisher()

    def source(f, fetched_at):
        if f.field_id == "a":
            raise TimeoutError("Open-Meteo fora")
        return readings(fetched_at)

    results = collect([field("a"), field("b")], source, store, publisher, FETCHED)

    assert isinstance(results[("p1", "a")], TimeoutError)
    assert len(results[("p1", "b")]) == 3
