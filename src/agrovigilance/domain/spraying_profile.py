"""Limites da janela de pulverização por cultura, com ajustes por contexto (ADR-0024).

Só dados e a resolução do perfil: a avaliação fica em `spraying_window.py`.
Cada limite guarda o motivo e a fonte, porque a explicação do alerta sai daqui.
"""

from dataclasses import dataclass, field, fields, replace
from enum import StrEnum
from typing import Any


@dataclass(frozen=True)
class ApplicationContext:
    """O que se sabe da aplicação. Só a cultura é obrigatória; o resto entra quando houver dado."""

    crop: str
    region: str | None = None  # ex.: UF, "ES"
    producer: str | None = None  # tenant_id: o que o próprio produtor decidiu tolerar
    equipment: str | None = None  # "trator", "drone", "costal"
    product_class: str | None = None  # ex.: "biologico", "herbicida"
    brand: str | None = None
    product: str | None = None  # ex.: "opera", "priori_xtra"


# Empate no tamanho do `match`: vale o campo mais específico. Do geral para o particular.
PRECEDENCE = {
    "region": 0,
    "producer": 1,
    "equipment": 2,
    "product_class": 3,
    "brand": 4,
    "product": 5,
}


class BoundKind(StrEnum):
    MIN = "min"  # o valor precisa ficar acima
    MAX = "max"  # o valor precisa ficar abaixo


class Severity(StrEnum):
    OK = "ok"
    TOLERABLE = "tolerable"  # fora do ideal, mas dentro da faixa tolerável
    BLOCKING = "blocking"


@dataclass(frozen=True)
class Bound:
    kind: BoundKind
    ideal: float
    tolerable: float | None  # None: não há faixa tolerável, passou do ideal bloqueia
    reason: str
    source: str

    def __post_init__(self):
        if self.tolerable is None:
            return
        looser = (
            self.tolerable < self.ideal
            if self.kind is BoundKind.MIN
            else self.tolerable > self.ideal
        )
        if not looser:
            raise ValueError(f"faixa tolerável {self.tolerable} não é mais frouxa que {self.ideal}")

    def check(self, value: float) -> Severity:
        def within(limit: float) -> bool:
            return value >= limit if self.kind is BoundKind.MIN else value <= limit

        if within(self.ideal):
            return Severity.OK
        if self.tolerable is not None and within(self.tolerable):
            return Severity.TOLERABLE
        return Severity.BLOCKING


@dataclass(frozen=True)
class SprayingProfile:
    wind_min_kmh: Bound | None  # a 2 m de altura; None: sem mínimo (ex.: trator, drone)
    wind_max_kmh: Bound  # a 2 m de altura
    temperature_max_c: Bound
    humidity_min_pct: Bound
    rain_probability_max_pct: Bound  # vale na aplicação, nas horas sem chuva e no resto do dia
    application_hours: int  # sessão de aplicação a partir da hora agendada
    rainfree_hours_after: int  # quanto tempo o produto precisa de folha seca depois


@dataclass(frozen=True)
class ProfileAdjustment:
    """Troca campos do perfil quando todos os campos de `match` batem com o contexto."""

    match: dict[str, str]  # campos de ApplicationContext
    changes: dict[str, Any] = field(default_factory=dict)  # campos de SprayingProfile

    def __post_init__(self):
        # Chave com erro de digitação nunca casaria e o ajuste sumiria em silêncio.
        if not self.match or set(self.match) - set(PRECEDENCE):
            raise ValueError(f"match inválido: {self.match}")
        profile_fields = {f.name for f in fields(SprayingProfile)}
        if set(self.changes) - profile_fields:
            raise ValueError(f"changes inválido: {set(self.changes) - profile_fields}")

    def applies_to(self, context: ApplicationContext) -> bool:
        return all(getattr(context, k) == v for k, v in self.match.items())

    def order(self) -> tuple[int, int]:
        return len(self.match), max(PRECEDENCE[k] for k in self.match)


ANTUNIASSI = "Antuniassi & Baio (2004), Boletim SBMET; Embrapa, Documentos 102"
PRODUCER = "produtor (resposta de 2026-11-26)"
EVAPORATION = "com o ar seco a gota evapora antes de chegar na folha"
DRIFT = "com vento forte o produto é levado para fora do alvo (deriva)"


def bula(product: str, version: str) -> str:
    return f"bula do {product} ({version})"


COFFEE = SprayingProfile(
    wind_min_kmh=Bound(
        BoundKind.MIN,
        3,
        None,
        reason="sem vento há risco de inversão térmica: a gota fina fica suspensa e deriva",
        source=ANTUNIASSI,
    ),
    wind_max_kmh=Bound(BoundKind.MAX, 10, None, reason=DRIFT, source=ANTUNIASSI),
    temperature_max_c=Bound(
        BoundKind.MAX,
        30,
        None,
        reason="no calor a gota evapora antes de chegar na folha "
        "(a evaporação dobra a cada 10 °C a mais)",
        source=ANTUNIASSI,
    ),
    humidity_min_pct=Bound(
        BoundKind.MIN,
        55,
        50,
        reason=EVAPORATION,
        source="Antuniassi (mínimo 55%); Embrapa, Documentos 102 (50 a 55%)",
    ),
    rain_probability_max_pct=Bound(
        BoundKind.MAX,
        30,
        50,
        reason="a chuva lava o produto da folha antes de ele ser absorvido",
        source="faixas do projeto sobre a probabilidade da Open-Meteo (ADR-0024)",
    ),
    application_hours=2,
    # Contra praga, pelo menos 5 a 6 h; a bula de cada produto ajusta (ADR-0024).
    rainfree_hours_after=6,
)

BASE_PROFILES: dict[str, SprayingProfile] = {"cafe": COFFEE}

# Cada fator mexe só no que é dele (ADR-0024): o produtor na temperatura, o equipamento no vento
# mínimo e o produto (ou a classe) na umidade, no vento máximo e no tempo sem chuva.
# O que é de um produtor (ex.: calor tolerável) é dado dele e vem do cadastro, não daqui.
ADJUSTMENTS: tuple[ProfileAdjustment, ...] = (
    # Equipamento
    ProfileAdjustment({"equipment": "trator"}, {"wind_min_kmh": None}),  # o turbo empurra a gota
    ProfileAdjustment({"equipment": "drone"}, {"wind_min_kmh": None}),  # o rotor empurra a gota
    ProfileAdjustment(
        {"equipment": "costal"},
        {
            "wind_min_kmh": Bound(
                BoundKind.MIN,
                3,
                0,
                reason="sem vento há risco de inversão térmica; com gota grossa o risco é menor",
                source=f"{ANTUNIASSI}; {PRODUCER} (calmaria é melhor no mato)",
            )
        },
    ),
    # Classe de produto
    ProfileAdjustment(
        {"product_class": "biologico"},
        {
            "humidity_min_pct": Bound(
                BoundKind.MIN,
                65,
                None,
                reason="o fungo do biológico precisa de ar úmido para sobreviver na folha",
                source="Incaper, Documentos 266 (2019): Beauveria só com umidade acima de 65%",
            )
        },
    ),
    ProfileAdjustment({"product_class": "herbicida"}, {"rainfree_hours_after": 2}),  # produtor
    # Produto (terrestre)
    ProfileAdjustment(
        {"product": "priori_xtra"},
        {
            "humidity_min_pct": Bound(
                BoundKind.MIN,
                50,
                None,
                reason=EVAPORATION,
                source=bula("Priori Xtra", "25/06/2025"),
            ),
            "wind_max_kmh": Bound(
                BoundKind.MAX, 15, None, reason=DRIFT, source=bula("Priori Xtra", "25/06/2025")
            ),
        },
    ),
    ProfileAdjustment(
        {"product": "opera"},
        {
            "humidity_min_pct": Bound(
                BoundKind.MIN,
                60,
                None,
                reason=EVAPORATION,
                source=bula("Opera", "rev. 16, 18/07/2025"),
            ),
            "rainfree_hours_after": 4,  # "chuva dentro de 4 horas pode afetar o desempenho"
        },
    ),
    ProfileAdjustment(
        {"product": "altacor"},
        {
            "wind_max_kmh": Bound(
                BoundKind.MAX, 15, None, reason=DRIFT, source=bula("Altacor", "05/08/2026")
            )
        },
    ),
    ProfileAdjustment(
        {"product": "marshal"},
        {
            "humidity_min_pct": Bound(
                BoundKind.MIN, 50, None, reason=EVAPORATION, source=bula("Marshal", "FMC")
            )
        },
    ),
    ProfileAdjustment({"product": "roundup"}, {"rainfree_hours_after": 4}),  # bula Original DI
)


def resolve_profile(
    context: ApplicationContext,
    base_profiles: dict[str, SprayingProfile] = BASE_PROFILES,
    adjustments: tuple[ProfileAdjustment, ...] = ADJUSTMENTS,
) -> SprayingProfile:
    """Perfil base da cultura + ajustes que casam, do mais geral para o mais específico."""
    try:
        profile = base_profiles[context.crop]
    except KeyError:
        raise ValueError(f"sem perfil de pulverização para a cultura {context.crop!r}") from None
    matching = [a for a in adjustments if a.applies_to(context)]
    for adjustment in sorted(matching, key=ProfileAdjustment.order):  # empate total: ordem da lista
        profile = replace(profile, **adjustment.changes)
    return profile
