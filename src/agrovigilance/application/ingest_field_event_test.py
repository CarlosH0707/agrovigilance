import uuid

from agrovigilance.application.ingest_field_event import ingest
from agrovigilance.domain.field_event import FieldEvent

PAYLOAD = {
    "tenant_id": "t1",
    "field_id": "f1",
    "type": "spray_scheduled",
    "occurred_at": "2026-11-25T10:00:00Z",
    "product": "glifosato",
}


class FakeStore:
    def __init__(self):
        self.rows = {}

    def insert(self, key, event, payload):
        if key in self.rows:
            return None
        self.rows[key] = (uuid.uuid4(), payload)
        return self.rows[key][0]


class FakePublisher:
    def __init__(self):
        self.messages = []

    def publish(self, message):
        self.messages.append(message)


def test_new_event_is_stored_and_published_once():
    store, publisher = FakeStore(), FakePublisher()

    event_id = ingest(FieldEvent(**PAYLOAD), PAYLOAD, store, publisher)

    assert event_id is not None
    assert publisher.messages == [
        {"source": "field_events", "event_id": str(event_id), "tenant_id": "t1", "field_id": "f1"}
    ]


def test_duplicate_is_not_published_again():
    store, publisher = FakeStore(), FakePublisher()
    ingest(FieldEvent(**PAYLOAD), PAYLOAD, store, publisher)

    assert ingest(FieldEvent(**PAYLOAD), PAYLOAD, store, publisher) is None
    assert len(store.rows) == 1
    assert len(publisher.messages) == 1
