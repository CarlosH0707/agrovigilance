from dataclasses import replace
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from agrovigilance.domain.spraying_profile import COFFEE, Severity
from agrovigilance.domain.spraying_window import SAME_DAY_RAIN, HourForecast, Level, assess

TZ = ZoneInfo("America/Sao_Paulo")  # UTC-3, sem horário de verão
NOW = datetime(2026, 11, 26, 10, 20, tzinfo=UTC)  # 7h20 em Brasília: at(i) = 7h + i local
NOW_HOUR = NOW.replace(minute=0)
# COFFEE: aplicação de 2 h + 6 h sem chuva; at(17) já é 0h do dia seguinte.
GOOD = {
    "temperature_c": 24.0,
    "relative_humidity_pct": 75.0,
    "precipitation_probability_pct": 10.0,
    "wind_speed_kmh": 6.0,  # 4,5 km/h a 2 m
}
RAIN = {"precipitation_probability_pct": 90}


def forecast(hours=72 + 12, **overrides_by_offset):
    """Horas boas a partir de NOW_HOUR; `h3={"wind_speed_kmh": 15}` muda a hora NOW_HOUR+3."""
    return [
        HourForecast(
            target_hour=NOW_HOUR + timedelta(hours=i),
            **{**GOOD, **overrides_by_offset.get(f"h{i}", {})},
        )
        for i in range(hours)
    ]


def at(offset):
    return NOW_HOUR + timedelta(hours=offset)


def rain(offsets):
    return {f"h{i}": RAIN for i in offsets}


def calm_except(*offsets):
    """Calmaria (bloqueia) em todas as horas, menos nas indicadas."""
    return {f"h{i}": {"wind_speed_kmh": 1} for i in range(84) if i not in offsets}


def assess_coffee(scheduled_for, hours, profile=COFFEE, tz=TZ, **kwargs):
    return assess(scheduled_for, hours, profile, NOW, tz, **kwargs)


def test_good_weather_is_ok():
    result = assess_coffee(at(3), forecast())
    assert result.level is Level.OK
    assert result.violations == ()


def test_tolerable_humidity_is_attention():
    result = assess_coffee(at(3), forecast(h4={"relative_humidity_pct": 52}))
    assert result.level is Level.ATTENTION
    [violation] = result.violations
    assert (violation.condition, violation.target_hour, violation.value) == (
        "humidity_min_pct",
        at(4),
        52,
    )
    assert violation.severity is Severity.TOLERABLE


def test_application_hours_check_every_condition():
    # Aplicação de 2 h a partir de 3: horas 3 e 4. Calmaria na 3, calor na 4.
    result = assess_coffee(at(3), forecast(h3={"wind_speed_kmh": 1}, h4={"temperature_c": 33}))
    assert {(v.condition, v.target_hour) for v in result.violations} == {
        ("wind_min_kmh", at(3)),
        ("temperature_max_c", at(4)),
    }


def test_wind_is_judged_at_2_m():
    # 13 km/h a 10 m ≈ 9,7 km/h a 2 m: passa. 14 km/h ≈ 10,5 km/h: bloqueia.
    assert assess_coffee(at(3), forecast(h3={"wind_speed_kmh": 13})).level is Level.OK
    result = assess_coffee(at(3), forecast(h3={"wind_speed_kmh": 14}))
    [violation] = result.violations
    assert (violation.condition, violation.value) == ("wind_max_kmh", 10.5)


def test_profile_without_wind_minimum_accepts_calm():
    tractor = replace(COFFEE, wind_min_kmh=None)
    assert assess_coffee(at(3), forecast(h3={"wind_speed_kmh": 0}), tractor).level is Level.OK


def test_rainfree_hours_only_check_rain():
    # Depois da aplicação (horas 5 a 10) só a chuva importa: vento forte ali não pesa.
    assert assess_coffee(at(3), forecast(h6={"wind_speed_kmh": 30})).level is Level.OK

    result = assess_coffee(at(3), forecast(h10=RAIN))
    [violation] = result.violations
    assert (violation.condition, violation.target_hour) == ("rain_probability_max_pct", at(10))
    assert violation.severity is Severity.BLOCKING


def test_rain_later_the_same_day_is_attention():
    result = assess_coffee(at(3), forecast(h12=RAIN))  # 19h locais
    assert result.level is Level.ATTENTION
    [violation] = result.violations
    assert (violation.condition, violation.severity) == (SAME_DAY_RAIN, Severity.TOLERABLE)


def test_rain_on_the_next_day_does_not_matter():
    assert assess_coffee(at(3), forecast(h17=RAIN)).level is Level.OK  # 0h do dia seguinte


def test_blocked_with_a_good_window_later_suggests_the_first_one():
    # Chuva das 7h às 20h locais: o tempo libera às 21h, mas a sugestão espera o dia seguinte.
    result = assess_coffee(at(3), forecast(**rain(range(14))))
    assert result.level is Level.POSTPONE
    assert result.suggested_start == at(23)  # 6h do dia seguinte


def test_suggestion_can_be_earlier_than_the_schedule():
    result = assess_coffee(at(10), forecast(h10={"wind_speed_kmh": 20}))
    assert result.level is Level.POSTPONE
    assert result.suggested_start == at(0)


def test_suggestion_accepts_rain_later_the_same_day():
    result = assess_coffee(at(3), forecast(h3={"wind_speed_kmh": 20}, **rain(range(12, 17))))
    assert result.suggested_start == at(0)


def test_suggestion_ignores_windows_that_are_only_tolerable():
    humid = {f"h{i}": {"relative_humidity_pct": 52} for i in range(84)}
    humid["h3"] = {"relative_humidity_pct": 52, "wind_speed_kmh": 20}
    assert assess_coffee(at(3), forecast(**humid)).level is Level.NO_WINDOW


def test_no_good_window_within_horizon_is_no_window():
    # Chuva até a hora 72; a hora 73 (8h locais) seria boa, mas passa das 72 h.
    hours = forecast(hours=200, **rain(range(73)))
    result = assess_coffee(at(3), hours)
    assert result.level is Level.NO_WINDOW
    assert result.suggested_start is None

    result = assess_coffee(at(3), hours, horizon=timedelta(hours=73))
    assert result.suggested_start == at(73)


def test_schedule_beyond_forecast_is_not_assessed_yet():
    assert assess_coffee(at(80), forecast(hours=84)) is None  # faltam as horas sem chuva


def test_missing_value_is_not_assessed():
    assert assess_coffee(at(3), forecast(h4={"wind_speed_kmh": None})) is None


def test_past_schedule_is_not_assessed():
    assert assess_coffee(at(-1), forecast()) is None


def test_schedule_in_the_current_hour_is_assessed():
    assert assess_coffee(NOW, forecast()).level is Level.OK


def test_stale_hours_from_the_snapshot_are_ignored():
    # Hora vencida com tempo bom não pode virar sugestão.
    stale = HourForecast(target_hour=at(-1), **GOOD)
    result = assess_coffee(at(3), [stale, *forecast(**rain(range(84)))])
    assert result.level is Level.NO_WINDOW


def test_profile_drives_the_window_length():
    longer = replace(COFFEE, application_hours=3, rainfree_hours_after=0)
    result = assess_coffee(at(3), forecast(h5={"temperature_c": 35}), longer)
    assert [v.target_hour for v in result.violations] == [at(5)]


def test_last_suggested_start_ends_the_application_at_18h():
    # 16h + 2 h termina às 18h: ainda vale. As horas sem chuva depois podem passar das 18h.
    assert assess_coffee(at(3), forecast(**calm_except(9, 10))).suggested_start == at(9)


def test_never_suggests_an_application_that_ends_after_18h():
    # 17h + 2 h terminaria às 19h.
    assert assess_coffee(at(3), forecast(**calm_except(10, 11))).level is Level.NO_WINDOW


def test_never_suggests_before_6h():
    # 5h e 6h do dia seguinte são boas, mas começar às 5h não pode.
    assert assess_coffee(at(3), forecast(**calm_except(22, 23))).level is Level.NO_WINDOW
    assert assess_coffee(at(3), forecast(**calm_except(23, 24))).suggested_start == at(23)


def test_guardrail_uses_the_field_timezone():
    # Horas 21 e 22: 4h e 5h em Brasília, mas 7h e 8h em UTC.
    hours = forecast(**calm_except(21, 22))
    assert assess_coffee(at(3), hours).level is Level.NO_WINDOW
    assert assess_coffee(at(3), hours, tz=UTC).suggested_start == at(21)


def test_producer_schedule_outside_daytime_is_still_assessed():
    # O guardrail vale para a sugestão; agendar às 5h é escolha do produtor.
    assert assess_coffee(at(22), forecast()).level is Level.OK


def test_reads_the_snapshot_json_format():
    item = {
        "target_hour": "2026-11-26T15:00:00+00:00",
        "fetched_at": "2026-11-26T06:00:05+00:00",
        "temperature_c": 28.4,
        "relative_humidity_pct": 61,
        "precipitation_probability_pct": 10,
        "wind_speed_kmh": 7.2,
    }
    hour = HourForecast.from_snapshot(item)
    assert hour.target_hour == datetime(2026, 11, 26, 15, tzinfo=UTC)
    assert hour.wind_speed_kmh == 7.2
