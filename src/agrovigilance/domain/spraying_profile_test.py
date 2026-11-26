from dataclasses import replace

import pytest

from agrovigilance.domain.spraying_profile import (
    ADJUSTMENTS,
    COFFEE,
    ApplicationContext,
    Bound,
    BoundKind,
    ProfileAdjustment,
    Severity,
    resolve_profile,
)


def bound(kind, ideal, tolerable=None):
    return Bound(kind, ideal, tolerable, reason="r", source="s")


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (30, Severity.OK),
        (31, Severity.TOLERABLE),
        (34, Severity.TOLERABLE),
        (34.1, Severity.BLOCKING),
    ],
)
def test_max_bound_is_inclusive(value, expected):
    assert bound(BoundKind.MAX, 30, 34).check(value) is expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (55, Severity.OK),
        (52, Severity.TOLERABLE),
        (50, Severity.TOLERABLE),
        (49, Severity.BLOCKING),
    ],
)
def test_min_bound_is_inclusive(value, expected):
    assert bound(BoundKind.MIN, 55, 50).check(value) is expected


def test_bound_without_tolerance_blocks_right_after_ideal():
    assert bound(BoundKind.MAX, 10).check(10.1) is Severity.BLOCKING


@pytest.mark.parametrize(
    ("kind", "ideal", "tolerable"), [(BoundKind.MAX, 30, 28), (BoundKind.MIN, 55, 60)]
)
def test_tolerance_must_be_looser_than_ideal(kind, ideal, tolerable):
    with pytest.raises(ValueError):
        bound(kind, ideal, tolerable)


def test_coffee_without_adjustments_is_the_base_profile():
    assert resolve_profile(ApplicationContext(crop="cafe", region="ES")) is COFFEE


def test_unknown_crop_fails_loudly():
    with pytest.raises(ValueError, match="soja"):
        resolve_profile(ApplicationContext(crop="soja"))


def test_matching_adjustments_apply_from_least_to_most_specific():
    hot = bound(BoundKind.MAX, 30, 34)
    hotter = bound(BoundKind.MAX, 30, 35)
    humid = bound(BoundKind.MIN, 65)
    adjustments = (
        # Mais específico primeiro na lista: a ordem final vem do tamanho do match.
        ProfileAdjustment(
            {"region": "ES", "equipment": "turboatomizador"}, {"temperature_max_c": hotter}
        ),
        ProfileAdjustment({"region": "ES"}, {"temperature_max_c": hot}),
        ProfileAdjustment({"product_class": "biologico"}, {"humidity_min_pct": humid}),
        ProfileAdjustment({"region": "MG"}, {"application_hours": 9}),
    )
    context = ApplicationContext(
        crop="cafe", region="ES", product_class="biologico", equipment="turboatomizador"
    )

    profile = resolve_profile(context, adjustments=adjustments)

    assert profile.temperature_max_c is hotter
    assert profile.humidity_min_pct is humid
    assert profile.application_hours == COFFEE.application_hours
    assert profile.wind_max_kmh is COFFEE.wind_max_kmh


def test_adjustment_that_does_not_match_changes_nothing():
    adjustments = (ProfileAdjustment({"region": "ES"}, {"application_hours": 9}),)
    assert resolve_profile(ApplicationContext(crop="cafe"), adjustments=adjustments) is COFFEE


@pytest.mark.parametrize(
    ("match", "changes"),
    [
        ({"regiao": "ES"}, {}),  # campo de contexto com erro de digitação
        ({}, {"application_hours": 3}),  # match vazio valeria para tudo
        ({"crop": "cafe"}, {}),  # cultura escolhe o perfil base, não um ajuste
        ({"region": "ES"}, {"temperatura": 1}),  # campo de perfil inexistente
    ],
)
def test_invalid_adjustment_is_rejected(match, changes):
    with pytest.raises(ValueError):
        ProfileAdjustment(match, changes)


def test_product_beats_product_class_on_a_tie():
    # Mesmo tamanho de match: o campo mais específico vence, seja qual for a ordem na lista.
    adjustments = (
        ProfileAdjustment({"product": "x"}, {"rainfree_hours_after": 4}),
        ProfileAdjustment({"product_class": "herbicida"}, {"rainfree_hours_after": 2}),
    )
    context = ApplicationContext(crop="cafe", product_class="herbicida", product="x")
    assert resolve_profile(context, adjustments=adjustments).rainfree_hours_after == 4


def test_producer_adjustment_from_outside_combines_with_the_registered_ones():
    # Ajuste do produtor vem do cadastro e entra junto com os do código.
    heat = bound(BoundKind.MAX, 30, 35)
    producer = ProfileAdjustment({"producer": "p1"}, {"temperature_max_c": heat})
    profile = resolve_profile(
        ApplicationContext(crop="cafe", producer="p1", equipment="trator", product="opera"),
        adjustments=(*ADJUSTMENTS, producer),
    )
    assert profile.temperature_max_c is heat
    assert profile.wind_min_kmh is None  # trator: sem mínimo de vento
    assert (profile.temperature_max_c.ideal, profile.temperature_max_c.tolerable) == (30, 35)
    assert profile.humidity_min_pct.ideal == 60  # bula do Opera
    assert profile.rainfree_hours_after == 4  # bula do Opera
    assert profile.wind_max_kmh is COFFEE.wind_max_kmh


def test_biological_needs_humid_air():
    profile = resolve_profile(ApplicationContext(crop="cafe", product_class="biologico"))
    assert profile.humidity_min_pct.ideal == 65
    assert profile.rainfree_hours_after == COFFEE.rainfree_hours_after


def test_backpack_sprayer_turns_calm_into_attention():
    profile = resolve_profile(ApplicationContext(crop="cafe", equipment="costal"))
    assert profile.wind_min_kmh.check(0) is Severity.TOLERABLE


def test_herbicide_label_beats_the_producer_rule_of_thumb():
    herbicide = ApplicationContext(crop="cafe", product_class="herbicida")
    assert resolve_profile(herbicide).rainfree_hours_after == 2
    roundup = replace(herbicide, product="roundup")
    assert resolve_profile(roundup).rainfree_hours_after == 4


def test_every_registered_adjustment_resolves():
    # Pega erro de digitação nos ajustes reais: todo campo trocado precisa existir no perfil.
    for adjustment in ADJUSTMENTS:
        context = ApplicationContext(crop="cafe", **adjustment.match)
        resolve_profile(context)
