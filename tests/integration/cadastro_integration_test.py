"""Cadastro (ADR-0026): o banco garante unicidade, formatos e que o talhão é do mesmo produtor."""

from zoneinfo import ZoneInfo

import psycopg
import pytest

from agrovigilance.infrastructure.database.core.fields.repository import FieldRepository
from scripts.migrate import migrate

pytestmark = pytest.mark.integration


@pytest.fixture
def conn(db):
    migrate(db)
    with psycopg.connect(db, autocommit=True) as conn:
        yield conn


def producer(conn, name="Fulano"):
    return conn.execute(
        "INSERT INTO core.producers (name) VALUES (%s) RETURNING id", (name,)
    ).fetchone()[0]


def farm(conn, producer_id, timezone="America/Sao_Paulo", region="ES"):
    return conn.execute(
        """INSERT INTO core.farms (producer_id, name, region, timezone, total_area_ha)
           VALUES (%s, 'Sede', %s, %s, 50) RETURNING id""",
        (producer_id, region, timezone),
    ).fetchone()[0]


def field(conn, producer_id, farm_id, field_id="cafe", latitude=-19.0):
    conn.execute(
        """INSERT INTO core.fields
               (producer_id, field_id, farm_id, name, crop, area_ha, latitude, longitude)
           VALUES (%s, %s, %s, 'Café', 'cafe', 36, %s, -40.0)""",
        (producer_id, field_id, farm_id, latitude),
    )


def contact(conn, producer_id, phone):
    conn.execute(
        "INSERT INTO core.producer_contacts (producer_id, name, phone) VALUES (%s, 'X', %s)",
        (producer_id, phone),
    )


def test_homonymous_producers_are_different_tenants(conn):
    assert producer(conn, "Caliman") != producer(conn, "Caliman")


def test_a_phone_belongs_to_one_contact_only(conn):
    first, second = producer(conn), producer(conn)
    contact(conn, first, "+5527999990000")
    with pytest.raises(psycopg.errors.UniqueViolation):
        contact(conn, second, "+5527999990000")


@pytest.mark.parametrize("phone", ["27999990000", "+55 27 99999-0000", "+0123456789", "+55"])
def test_phone_must_be_e164(conn, phone):
    with pytest.raises(psycopg.errors.CheckViolation):
        contact(conn, producer(conn), phone)


def test_unknown_timezone_is_refused(conn):
    with pytest.raises(psycopg.errors.InvalidParameterValue):
        farm(conn, producer(conn), timezone="America/Vitoria_do_Nada")


@pytest.mark.parametrize("region", ["es", "ESP"])
def test_region_is_an_uppercase_uf(conn, region):
    with pytest.raises(psycopg.errors.CheckViolation):
        farm(conn, producer(conn), region=region)


def test_field_cannot_point_to_another_producers_farm(conn):
    mine, theirs = producer(conn), producer(conn)
    their_farm = farm(conn, theirs)
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        field(conn, mine, their_farm)


@pytest.mark.parametrize(
    ("field_id", "latitude"),
    [("Café", -19.0), ("a:b", -19.0), ("cafe", -91.0)],  # field_id vai nas chaves com ":"
)
def test_field_id_and_coordinates_are_checked(conn, field_id, latitude):
    p = producer(conn)
    with pytest.raises(psycopg.errors.CheckViolation):
        field(conn, p, farm(conn, p), field_id, latitude)


def test_list_all_brings_farm_data_and_the_producer_tolerance_for_the_crop(conn):
    p = producer(conn)
    field(conn, p, farm(conn, p))
    conn.execute(
        """INSERT INTO core.producer_crops (producer_id, crop, temperature_tolerable_max_c)
           VALUES (%s, 'cafe', 35), (%s, 'milho', 32)""",
        (p, p),
    )
    other = producer(conn)
    field(conn, other, farm(conn, other))  # sem tolerância cadastrada

    fields = {f.producer_id: f for f in FieldRepository(conn).list_all()}

    mine = fields[str(p)]
    assert (mine.field_id, mine.crop, mine.area_ha) == ("cafe", "cafe", 36)
    assert (mine.region, mine.timezone) == ("ES", ZoneInfo("America/Sao_Paulo"))
    assert mine.temperature_tolerable_max_c == 35  # a do café, não a do milho
    assert fields[str(other)].temperature_tolerable_max_c is None
