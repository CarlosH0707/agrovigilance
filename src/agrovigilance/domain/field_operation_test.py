from datetime import UTC, datetime, timedelta, timezone
from uuid import uuid4

import pytest

from agrovigilance.domain.field_operation import (
    Equipment,
    InvalidFieldOperation,
    OperationType,
    from_raw,
)
from agrovigilance.domain.products import ProductClass

OCCURRED = datetime(2026, 11, 25, 10, 0, tzinfo=UTC)


def convert(payload):
    return from_raw(uuid4(), "t1", "f1", OCCURRED, payload)


def test_done_spraying_needs_no_schedule():
    op = convert({"type": "pulverizacao_concluida"})
    assert op.type is OperationType.SPRAYING_DONE
    assert op.occurred_at == OCCURRED
    assert op.scheduled_for is None


def test_scheduled_spraying_keeps_the_instant():
    op = convert({"type": "pulverizacao_agendada", "scheduled_for": "2026-11-26T07:00:00-03:00"})
    assert op.scheduled_for == datetime(2026, 11, 26, 7, tzinfo=timezone(timedelta(hours=-3)))


@pytest.mark.parametrize("type_", ["colheita", "PULVERIZACAO_CONCLUIDA", "", None])
def test_rejects_type_outside_the_list(type_):
    with pytest.raises(InvalidFieldOperation, match="tipo fora da lista"):
        convert({"type": type_})


@pytest.mark.parametrize("scheduled_for", [None, "2026-11-26T07:00:00", "amanhã cedo"])
def test_rejects_schedule_without_aware_datetime(scheduled_for):
    payload = {"type": "pulverizacao_agendada", "scheduled_for": scheduled_for}
    with pytest.raises(InvalidFieldOperation, match="scheduled_for"):
        convert(payload)


def scheduled(**extra):
    return convert(
        {"type": "pulverizacao_agendada", "scheduled_for": "2026-11-26T07:00:00-03:00", **extra}
    )


def test_known_product_becomes_catalog_id_and_class():
    op = scheduled(product="Priori Xtra")
    assert (op.product, op.product_class) == ("priori_xtra", ProductClass.FUNGICIDE)


def test_unknown_product_is_kept_as_written():
    op = scheduled(product="  Clopam ")
    assert (op.product, op.product_class) == ("Clopam", None)


def test_unknown_product_keeps_the_informed_class():
    op = scheduled(product="Rite", product_class="herbicida")
    assert (op.product, op.product_class) == ("Rite", ProductClass.HERBICIDE)


def test_class_alone_is_enough_to_say_it_is_weed_control():
    op = scheduled(product_class="herbicida")
    assert (op.product, op.product_class) == (None, ProductClass.HERBICIDE)


def test_equipment_is_optional_and_never_assumed():
    assert scheduled().equipment is None
    assert scheduled(equipment="drone").equipment is Equipment.DRONE


@pytest.mark.parametrize(
    "extra",
    [
        {"equipment": "aviao"},
        {"equipment": ["trator"]},
        {"product_class": "adubo"},
        {"product": ""},
        {"product": 42},
        {"product": "Opera", "product_class": "herbicida"},  # Opera é fungicida
    ],
)
def test_invalid_product_or_equipment_is_rejected(extra):
    with pytest.raises(InvalidFieldOperation):
        scheduled(**extra)
