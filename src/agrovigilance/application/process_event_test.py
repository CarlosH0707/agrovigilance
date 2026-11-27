import json
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from agrovigilance.application.process_event import (
    handle,
    process_field_operation,
    process_weather,
)
from agrovigilance.domain.raw_event import RawEvent

NOW = datetime(2026, 11, 25, 12, tzinfo=UTC)
WEATHER_PAYLOAD = {
    "utc_offset_seconds": 0,
    "hourly_units": {
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


class FakeRaw:
    def __init__(self, *payloads):
        self.rows = {}
        for payload in payloads:
            row = RawEvent(uuid4(), "t1", "f1", NOW, NOW, payload)
            self.rows[row.id] = row
        self.status = {}

    def get(self, event_id):
        return self.rows.get(event_id)

    def set_status(self, event_id, status):
        self.status[event_id] = status


class FakeCore:
    def __init__(self):
        self.items = {}

    def insert(self, item):
        self.items.setdefault(item.raw_event_id, item)  # como o ON CONFLICT DO NOTHING


class FakeSnapshot:
    def __init__(self):
        self.refreshed = []

    def refresh(self, tenant_id, field_id):
        self.refreshed.append((tenant_id, field_id))


class FakeFields:
    def __init__(self, *registered):
        self.registered = set(registered) or {("t1", "f1")}

    def exists(self, tenant_id, field_id):
        return (tenant_id, field_id) in self.registered


def only_id(raw):
    [event_id] = raw.rows
    return event_id


def test_weather_goes_to_core_and_raw_is_processed():
    raw, core, snapshot = FakeRaw(WEATHER_PAYLOAD), FakeCore(), FakeSnapshot()
    event_id = only_id(raw)

    assert process_weather(event_id, raw, core, snapshot) == "processed"
    assert core.items[event_id].wind_speed_kmh == 7.2
    assert core.items[event_id].fetched_at == NOW  # o ingested_at do raw
    assert snapshot.refreshed == [("t1", "f1")]
    assert raw.status == {event_id: "processed"}


def test_processing_twice_keeps_one_canonical_row():
    raw, core, snapshot = FakeRaw({"type": "pulverizacao_concluida"}), FakeCore(), FakeSnapshot()
    event_id = only_id(raw)

    process_field_operation(event_id, raw, core, snapshot, FakeFields())
    process_field_operation(event_id, raw, core, snapshot, FakeFields())
    assert list(core.items) == [event_id]
    assert snapshot.refreshed == [("t1", "f1")] * 2  # recalcular de novo é inofensivo
    assert raw.status == {event_id: "processed"}


def test_invalid_operation_is_rejected_without_error():
    raw, core, snapshot = FakeRaw({"type": "colheita"}), FakeCore(), FakeSnapshot()
    event_id = only_id(raw)

    assert process_field_operation(event_id, raw, core, snapshot, FakeFields()) == "rejected"
    assert core.items == {}
    assert snapshot.refreshed == []
    assert raw.status == {event_id: "rejected"}


def test_bad_weather_unit_raises_so_the_message_goes_back():
    payload = {**WEATHER_PAYLOAD, "hourly_units": {}}
    raw, core, snapshot = FakeRaw(payload), FakeCore(), FakeSnapshot()

    with pytest.raises(ValueError, match="unidade"):
        process_weather(only_id(raw), raw, core, snapshot)
    assert snapshot.refreshed == []
    assert raw.status == {}


def test_missing_raw_row_raises():
    with pytest.raises(LookupError):
        process_weather(uuid4(), FakeRaw(), FakeCore(), FakeSnapshot())


def test_handle_routes_by_source():
    event_id = uuid4()
    seen = []
    handlers = {"field_events": lambda i: seen.append(i) or "processed"}
    body = json.dumps({"source": "field_events", "event_id": str(event_id), "tenant_id": "t1"})

    assert handle(body, handlers) == "processed"
    assert seen == [event_id]


@pytest.mark.parametrize(
    "body",
    [
        "não é json",
        json.dumps({"source": "outra_fonte", "event_id": str(uuid4())}),
        json.dumps({"source": "field_events", "event_id": "123"}),
    ],
)
def test_handle_refuses_malformed_message(body):
    with pytest.raises(ValidationError):
        handle(body, {"field_events": lambda i: "processed"})


def test_operation_for_an_unregistered_field_is_rejected():
    raw, core, snapshot = FakeRaw({"type": "pulverizacao_concluida"}), FakeCore(), FakeSnapshot()
    event_id = only_id(raw)

    status = process_field_operation(event_id, raw, core, snapshot, FakeFields(("t1", "outro")))

    assert status == "rejected"
    assert raw.status[event_id] == "rejected"
    assert core.items == {}
    assert snapshot.refreshed == []
