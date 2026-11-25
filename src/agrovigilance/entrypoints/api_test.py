import pytest
from fastapi.testclient import TestClient

from agrovigilance.application.ingest_field_event_test import FakePublisher, FakeStore
from agrovigilance.entrypoints.api import app, get_publisher, get_store

EVENT = {
    "tenant_id": "t1",
    "field_id": "f1",
    "type": "spray_scheduled",
    "occurred_at": "2026-11-25T10:00:00Z",
}


@pytest.fixture
def client():
    store, publisher = FakeStore(), FakePublisher()
    app.dependency_overrides = {get_store: lambda: store, get_publisher: lambda: publisher}
    yield TestClient(app), store, publisher
    app.dependency_overrides = {}


def test_first_post_is_accepted_and_repeat_is_duplicate(client):
    http, store, publisher = client

    first = http.post("/webhooks/field", json={**EVENT, "product": "glifosato"})
    again = http.post("/webhooks/field", json={**EVENT, "product": "glifosato"})

    assert first.status_code == 202
    assert first.json()["status"] == "accepted"
    assert again.status_code == 200
    assert again.json() == {"status": "duplicate"}
    assert len(publisher.messages) == 1
    [(_, payload)] = store.rows.values()
    assert payload["product"] == "glifosato"  # corpo bruto preservado


@pytest.mark.parametrize(
    "body",
    [{**EVENT, "occurred_at": "2026-11-25T10:00:00"}, {"tenant_id": "t1"}, ["not", "an", "object"]],
)
def test_invalid_body_is_422_and_nothing_happens(client, body):
    http, store, publisher = client

    assert http.post("/webhooks/field", json=body).status_code == 422
    assert store.rows == {} and publisher.messages == []
