"""Avalia a janela de pulverização agendada contra a previsão (ADR-0024).

Regra pura: recebe as horas de previsão do snapshot, o perfil e o horário atual.
"""

from dataclasses import dataclass
from datetime import datetime, time, timedelta, tzinfo
from enum import StrEnum
from typing import Any

from agrovigilance.domain.spraying_profile import Bound, Severity, SprayingProfile

HOUR = timedelta(hours=1)
# Previsão hora a hora é confiável o bastante para sugerir horário até aqui (ADR-0025).
SUGGESTION_HORIZON = timedelta(hours=72)
# Guardrail: nunca sugerir aplicação de madrugada ou à noite (6h às 18h), no horário local do talhão.
# Vale para qualquer perfil; o produtor só poderá apertar essa faixa (ADR-0024).
SUGGESTION_EARLIEST_START = time(6)
SUGGESTION_LATEST_END = time(18)
# A Open-Meteo dá o vento a 10 m; o bico fica perto de 2 m. Perfil logarítmico do vento,
# FAO-56, eq. 47: u2 = u10 * 4,87 / ln(67,8 * 10 - 5,42) ≈ 0,748.
WIND_10M_TO_2M = 0.748


class Level(StrEnum):
    OK = "ok"
    ATTENTION = "attention"  # algum valor na faixa tolerável
    POSTPONE = "postpone"  # bloqueado, mas há janela boa no horizonte
    NO_WINDOW = "no_window"  # bloqueado e sem janela boa no horizonte


@dataclass(frozen=True)
class HourForecast:
    target_hour: datetime
    temperature_c: float | None
    relative_humidity_pct: float | None
    precipitation_probability_pct: float | None
    wind_speed_kmh: float | None

    @classmethod
    def from_snapshot(cls, item: dict[str, Any]) -> HourForecast:
        """Um item do `forecast` JSONB de read.field_snapshot."""
        return cls(
            target_hour=datetime.fromisoformat(item["target_hour"]),
            temperature_c=item["temperature_c"],
            relative_humidity_pct=item["relative_humidity_pct"],
            precipitation_probability_pct=item["precipitation_probability_pct"],
            wind_speed_kmh=item["wind_speed_kmh"],
        )


@dataclass(frozen=True)
class Violation:
    target_hour: datetime
    condition: str  # campo do perfil (ex.: "wind_max_kmh") ou SAME_DAY_RAIN
    value: float  # vento já convertido para 2 m
    bound: Bound
    severity: Severity


@dataclass(frozen=True)
class Assessment:
    level: Level
    scheduled_for: datetime
    violations: tuple[Violation, ...]
    suggested_start: datetime | None = None


def _floor_hour(moment: datetime) -> datetime:
    return moment.replace(minute=0, second=0, microsecond=0)


SAME_DAY_RAIN = "rain_same_day"  # chuva no resto do dia: só pesa como atenção


def _wind_2m(forecast: HourForecast) -> float | None:
    if forecast.wind_speed_kmh is None:
        return None
    return round(forecast.wind_speed_kmh * WIND_10M_TO_2M, 1)


def _rain(forecast: HourForecast) -> float | None:
    return forecast.precipitation_probability_pct


# Condição do perfil → leitura da previsão.
_APPLICATION_CHECKS = {
    "wind_min_kmh": _wind_2m,
    "wind_max_kmh": _wind_2m,
    "temperature_max_c": lambda f: f.temperature_c,
    "humidity_min_pct": lambda f: f.relative_humidity_pct,
    "rain_probability_max_pct": _rain,
}
_RAINFREE_CHECKS = {"rain_probability_max_pct": _rain}


def check_start(
    start: datetime, by_hour: dict[datetime, HourForecast], profile: SprayingProfile, tz: tzinfo
) -> list[Violation] | None:
    """Violações de uma aplicação começando em `start`; None se falta previsão para decidir."""
    plan = [(start + i * HOUR, _APPLICATION_CHECKS) for i in range(profile.application_hours)]
    plan += [
        (start + (profile.application_hours + i) * HOUR, _RAINFREE_CHECKS)
        for i in range(profile.rainfree_hours_after)
    ]
    violations = []
    for hour, checks in plan:
        forecast = by_hour.get(hour)
        if forecast is None:
            return None
        for condition, read in checks.items():
            bound = getattr(profile, condition)
            if bound is None:  # limite desligado pelo perfil (ex.: vento mínimo no trator)
                continue
            value = read(forecast)
            if value is None:  # hora sem o dado: não dá para afirmar que está bom
                return None
            severity = bound.check(value)
            if severity is not Severity.OK:
                violations.append(Violation(hour, condition, value, bound, severity))

    # "O ideal é nem chover no dia": depois das horas sem chuva, até o fim do dia local, chuva
    # vira atenção, nunca bloqueio. Hora sem previsão aqui não impede a avaliação.
    hour = start + (profile.application_hours + profile.rainfree_hours_after) * HOUR
    while hour.astimezone(tz).date() == start.astimezone(tz).date():
        forecast = by_hour.get(hour)
        value = forecast and _rain(forecast)
        bound = profile.rain_probability_max_pct
        if value is not None and bound.check(value) is not Severity.OK:
            violations.append(Violation(hour, SAME_DAY_RAIN, value, bound, Severity.TOLERABLE))
        hour += HOUR
    return violations


def within_daytime(start: datetime, profile: SprayingProfile, tz: tzinfo) -> bool:
    """A aplicação inteira (não as horas sem chuva depois) cabe entre 6h e 18h locais."""
    local_start = start.astimezone(tz)
    local_end = (start + profile.application_hours * HOUR).astimezone(tz)
    return (
        local_start.time() >= SUGGESTION_EARLIEST_START
        and local_end.date() == local_start.date()
        and local_end.time() <= SUGGESTION_LATEST_END
    )


def assess(
    scheduled_for: datetime,
    forecast: list[HourForecast],
    profile: SprayingProfile,
    now: datetime,
    tz: tzinfo,
    horizon: timedelta = SUGGESTION_HORIZON,
) -> Assessment | None:
    """Nível da pulverização agendada. None quando não há o que dizer ainda.

    None: o agendamento já passou ou a previsão ainda não cobre a janela inteira.
    `tz` é o fuso do talhão. O guardrail de horário vale só para a sugestão: o agendamento
    do produtor (ex.: 5h, para fugir do calor) é avaliado pelo tempo, sem discussão.
    """
    now_hour = _floor_hour(now)
    start = _floor_hour(scheduled_for)
    if start < now_hour:
        return None
    # O snapshot pode ter hora vencida até o próximo refresh (ADR-0022).
    by_hour = {f.target_hour: f for f in forecast if f.target_hour >= now_hour}

    violations = check_start(start, by_hour, profile, tz)
    if violations is None:
        return None
    if not violations:
        return Assessment(Level.OK, scheduled_for, ())
    if all(v.severity is Severity.TOLERABLE for v in violations):
        return Assessment(Level.ATTENTION, scheduled_for, tuple(violations))

    candidate = now_hour
    while candidate <= now_hour + horizon:
        if within_daytime(candidate, profile, tz) and _is_good(
            check_start(candidate, by_hour, profile, tz)
        ):
            return Assessment(Level.POSTPONE, scheduled_for, tuple(violations), candidate)
        candidate += HOUR
    return Assessment(Level.NO_WINDOW, scheduled_for, tuple(violations))


def _is_good(violations: list[Violation] | None) -> bool:
    """Janela que pode ser sugerida: tudo ideal; chuva no fim do dia não impede."""
    return violations is not None and all(v.condition == SAME_DAY_RAIN for v in violations)
