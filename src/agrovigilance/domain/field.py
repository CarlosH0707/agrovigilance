"""Talhão cadastrado, com o que vem da propriedade e do produtor (ADR-0026)."""

from dataclasses import dataclass
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class Field:
    producer_id: str  # UUID do produtor; é o tenant_id dos eventos
    field_id: str
    name: str
    crop: str
    area_ha: float | None
    latitude: float
    longitude: float
    region: str  # UF da propriedade
    timezone: ZoneInfo  # fuso da propriedade
    temperature_tolerable_max_c: float | None  # do produtor para esta cultura
