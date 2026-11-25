"""Constraints das tabelas canônicas (ADR-0019): o banco repete as regras do domínio."""

import psycopg
import pytest

from scripts.migrate import migrate

pytestmark = pytest.mark.integration

RAW_FIELD_EVENT = """
    INSERT INTO raw.field_events (idempotency_key, tenant_id, field_id, occurred_at, payload)
    VALUES ('k1', 't1', 'f1', now(), '{}') RETURNING id
"""
RAW_WEATHER = """
    INSERT INTO raw.open_meteo_events (idempotency_key, tenant_id, field_id, occurred_at, payload)
    VALUES ('k1', 't1', 'f1', now(), '{}') RETURNING id
"""
OPERATION = """
    INSERT INTO core.field_operations
        (raw_event_id, tenant_id, field_id, type, occurred_at, scheduled_for)
    VALUES (%s, 't1', 'f1', %s, now(), %s)
    ON CONFLICT (raw_event_id) DO NOTHING
    RETURNING id
"""


@pytest.fixture
def conn(db):
    migrate(db)
    with psycopg.connect(db, autocommit=True) as conn:
        yield conn


def test_same_raw_event_becomes_one_operation(conn):
    raw_id = conn.execute(RAW_FIELD_EVENT).fetchone()[0]
    args = (raw_id, "pulverizacao_concluida", None)
    assert conn.execute(OPERATION, args).fetchone() is not None
    assert conn.execute(OPERATION, args).fetchone() is None
    assert conn.execute("SELECT count(*) FROM core.field_operations").fetchone() == (1,)


def test_same_raw_event_becomes_one_forecast(conn):
    raw_id = conn.execute(RAW_WEATHER).fetchone()[0]
    insert = """
        INSERT INTO core.weather_forecasts (raw_event_id, tenant_id, field_id, target_hour, fetched_at)
        VALUES (%s, 't1', 'f1', now(), now())
        ON CONFLICT (raw_event_id) DO NOTHING
        RETURNING id
    """
    assert conn.execute(insert, (raw_id,)).fetchone() is not None
    assert conn.execute(insert, (raw_id,)).fetchone() is None


@pytest.mark.parametrize(
    ("type_", "scheduled_for"),
    [("colheita", None), ("pulverizacao_agendada", None)],
)
def test_check_rejects_what_the_domain_rejects(conn, type_, scheduled_for):
    raw_id = conn.execute(RAW_FIELD_EVENT).fetchone()[0]
    with pytest.raises(psycopg.errors.CheckViolation):
        conn.execute(OPERATION, (raw_id, type_, scheduled_for))


def test_operation_needs_existing_raw_event(conn):
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        conn.execute(
            OPERATION, ("019ab000-0000-7000-8000-000000000000", "pulverizacao_concluida", None)
        )
