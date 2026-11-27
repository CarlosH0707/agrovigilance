import pytest

from agrovigilance.domain.products import CATALOG, ProductClass, find
from agrovigilance.domain.spraying_profile import ADJUSTMENTS


@pytest.mark.parametrize("text", ["Priori Xtra", "priori xtra", "PRIORI-XTRA", "priori_xtra"])
def test_finds_by_name_or_id_ignoring_case_and_separators(text):
    assert find(text).id == "priori_xtra"


def test_finds_ignoring_accents():
    assert find("Ópera").id == "opera"


def test_unknown_product_is_none():
    assert find("Clopam") is None
    assert find("") is None


def test_every_product_adjustment_points_to_a_catalog_product():
    # Ajuste com id que o catálogo não conhece nunca casaria com um agendamento.
    ids = {a.match["product"] for a in ADJUSTMENTS if "product" in a.match}
    assert ids <= set(CATALOG)


def test_every_product_class_adjustment_is_a_known_class():
    classes = {a.match["product_class"] for a in ADJUSTMENTS if "product_class" in a.match}
    assert classes <= {c.value for c in ProductClass}
