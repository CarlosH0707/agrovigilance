"""read.field_snapshot recalculado a partir de core (ADR-0022): ordem e repetição não mudam nada."""

from datetime import UTC, datetime, timedelta

import psycopg
import pytest

from agrovigilance.infrastructure.database.read.field_snapshot.repository import (
    FieldSnapshotRepository,
)
from scripts.migrate import migrate

pytestmark = pytest.mark.integration

NOW = datetime.now(UTC)
NEXT_HOUR = NOW.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
SNAPSHOT = """
    SELECT forecast, scheduled_spraying_for, last_operation_type, last_operation_at
    FROM read.field_snapshot WHERE tenant_id = 't1' AND field_id = 'f1'
"""


@pytest.fixture
def conn(db):
    migrate(db)
    with psycopg.connect(db, autocommit=True) as conn:
        yield conn


def raw_id(conn, table):
    return conn.execute(
        f"INSERT INTO raw.{table} (idempotency_key, tenant_id, field_id, occurred_at, payload)"
        " VALUES (gen_random_uuid()::text, 't1', 'f1', now(), '{}') RETURNING id"
    ).fetchone()[0]


def add_forecast(conn, target_hour, fetched_at, wind):
    conn.execute(
        "INSERT INTO core.weather_forecasts"
        " (raw_event_id, tenant_id, field_id, target_hour, fetched_at, wind_speed_kmh)"
        " VALUES (%s, 't1', 'f1', %s, %s, %s)",
        (raw_id(conn, "open_meteo_events"), target_hour, fetched_at, wind),
    )


def add_operation(conn, type_, occurred_at, scheduled_for=None):
    conn.execute(
        "INSERT INTO core.field_operations"
        " (raw_event_id, tenant_id, field_id, type, occurred_at, scheduled_for)"
        " VALUES (%s, 't1', 'f1', %s, %s, %s)",
        (raw_id(conn, "field_events"), type_, occurred_at, scheduled_for),
    )


def refresh(conn):
    FieldSnapshotRepository(conn).refresh("t1", "f1")
    return conn.execute(SNAPSHOT).fetchone()


def test_newest_fetch_wins_even_if_it_arrived_first(conn):
    add_forecast(conn, NEXT_HOUR, NOW, wind=5.0)  # coleta nova processada antes
    add_forecast(conn, NEXT_HOUR, NOW - timedelta(hours=1), wind=20.0)  # coleta velha chega depois

    [hour] = refresh(conn)[0]
    assert hour["wind_speed_kmh"] == 5.0
    assert datetime.fromisoformat(hour["target_hour"]) == NEXT_HOUR


def test_past_hours_are_left_out_and_hours_are_ordered(conn):
    add_forecast(conn, NEXT_HOUR + timedelta(hours=1), NOW, wind=2.0)
    add_forecast(conn, NEXT_HOUR, NOW, wind=1.0)
    add_forecast(conn, NEXT_HOUR - timedelta(hours=3), NOW, wind=9.0)

    forecast = refresh(conn)[0]
    assert [h["wind_speed_kmh"] for h in forecast] == [1.0, 2.0]


def test_refresh_twice_keeps_one_identical_row(conn):
    add_forecast(conn, NEXT_HOUR, NOW, wind=5.0)
    add_operation(conn, "pulverizacao_concluida", NOW)

    first = refresh(conn)
    assert refresh(conn) == first
    assert conn.execute("SELECT count(*) FROM read.field_snapshot").fetchone() == (1,)


def test_schedule_stays_open_until_a_later_completion(conn):
    when = NEXT_HOUR + timedelta(hours=5)
    add_operation(conn, "pulverizacao_agendada", NOW - timedelta(hours=2), when)
    assert refresh(conn)[1:] == (when, "pulverizacao_agendada", NOW - timedelta(hours=2))

    add_operation(conn, "pulverizacao_concluida", NOW)
    assert refresh(conn)[1:] == (None, "pulverizacao_concluida", NOW)


def test_completion_before_the_schedule_does_not_close_it(conn):
    when = NEXT_HOUR + timedelta(hours=5)
    add_operation(conn, "pulverizacao_concluida", NOW - timedelta(days=1))
    add_operation(conn, "pulverizacao_agendada", NOW, when)
    assert refresh(conn)[1] == when


def test_field_without_data_gets_an_empty_row(conn):
    assert refresh(conn) == ([], None, None, None)


def test_open_schedule_carries_its_product_and_equipment(conn):
    def schedule(occurred_at, product, product_class, equipment):
        conn.execute(
            "INSERT INTO core.field_operations (raw_event_id, tenant_id, field_id, type,"
            " occurred_at, scheduled_for, product, product_class, equipment)"
            " VALUES (%s, 't1', 'f1', 'pulverizacao_agendada', %s, %s, %s, %s, %s)",
            (
                raw_id(conn, "field_events"),
                occurred_at,
                NEXT_HOUR,
                product,
                product_class,
                equipment,
            ),
        )

    def scheduled():
        FieldSnapshotRepository(conn).refresh("t1", "f1")
        return conn.execute(
            "SELECT scheduled_product, scheduled_product_class, scheduled_equipment"
            " FROM read.field_snapshot WHERE tenant_id = 't1' AND field_id = 'f1'"
        ).fetchone()

    schedule(NOW - timedelta(hours=2), "opera", "fungicida", "trator")
    schedule(NOW - timedelta(hours=1), "Clopam", None, None)  # o último agendamento vale
    assert scheduled() == ("Clopam", None, None)

    add_operation(conn, "pulverizacao_concluida", NOW)
    assert scheduled() == (None, None, None)
