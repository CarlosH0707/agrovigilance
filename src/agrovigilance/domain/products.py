"""Catálogo dos produtos conhecidos, com a classe de cada um (ADR-0027).

O id é o que os ajustes de perfil usam (ADR-0024). Produto fora daqui é aceito no
agendamento, mas sem bula cadastrada a regra usa só a classe (se vier) ou o perfil base.
"""

import re
import unicodedata
from dataclasses import dataclass
from enum import StrEnum


class ProductClass(StrEnum):
    FUNGICIDE = "fungicida"
    INSECTICIDE = "inseticida"
    HERBICIDE = "herbicida"
    BIOLOGICAL = "biologico"


@dataclass(frozen=True)
class Product:
    id: str
    name: str
    product_class: ProductClass


CATALOG: dict[str, Product] = {
    p.id: p
    for p in (
        Product("priori_xtra", "Priori Xtra", ProductClass.FUNGICIDE),
        Product("opera", "Opera", ProductClass.FUNGICIDE),
        Product("altacor", "Altacor", ProductClass.INSECTICIDE),
        Product("marshal", "Marshal", ProductClass.INSECTICIDE),
        Product("curyom", "Curyom", ProductClass.INSECTICIDE),
        Product("roundup", "Roundup", ProductClass.HERBICIDE),
        Product("beauveria", "Beauveria bassiana", ProductClass.BIOLOGICAL),
    )
}


def _normalize(text: str) -> str:
    """'Priori Xtra', 'priori-xtra' e 'PRIORI_XTRA' viram 'priorixtra': sem acento nem símbolo."""
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", ascii_text.casefold())


_BY_KEY = {key: p for p in CATALOG.values() for key in (_normalize(p.id), _normalize(p.name))}


def find(text: str) -> Product | None:
    """Produto do catálogo pelo id ou pelo nome, sem ligar para caixa, acento e separador."""
    return _BY_KEY.get(_normalize(text))
