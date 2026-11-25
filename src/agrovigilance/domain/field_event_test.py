from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from agrovigilance.domain.field_event import FieldEvent, idempotency_key

BASE = {"tenant_id": "t1", "field_id": "f1", "type": "spray_scheduled"}


def event(**overrides):
    return FieldEvent(**{**BASE, "occurred_at": "2026-11-25T10:00:00Z", **overrides})


def test_key_uses_source_event_id_when_present():
    assert idempotency_key(event(source_event_id="abc")) == "field_event:abc"


def test_key_hash_is_deterministic_and_ignores_timezone_notation():
    brt = datetime(2026, 11, 25, 7, 0, tzinfo=timezone(timedelta(hours=-3)))

    key = idempotency_key(event())

    assert key == idempotency_key(event())
    assert key == idempotency_key(event(occurred_at=brt))
    assert key.startswith("field_event:") and len(key) == len("field_event:") + 64


@pytest.mark.parametrize(
    "change",
    [
        {"type": "spray_completed"},
        {"field_id": "f2"},
        {"tenant_id": "t2"},
        {"occurred_at": "2026-11-25T10:00:01Z"},
    ],
)
def test_key_hash_changes_with_identifying_fields(change):
    assert idempotency_key(event(**change)) != idempotency_key(event())


def test_naive_datetime_is_rejected():
    with pytest.raises(ValidationError):
        event(occurred_at="2026-11-25T10:00:00")


def test_missing_required_field_is_rejected():
    with pytest.raises(ValidationError):
        FieldEvent(tenant_id="t1", field_id="f1", occurred_at="2026-11-25T10:00:00Z")
