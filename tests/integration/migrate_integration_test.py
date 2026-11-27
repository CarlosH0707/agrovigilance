import shutil

import psycopg
import pytest

from scripts.migrate import MIGRATIONS_DIR, MigrationError, migrate

pytestmark = pytest.mark.integration

ALL = [
    "V0001__create_schemas.sql",
    "V0002__create_raw_open_meteo_events.sql",
    "V0003__create_raw_field_events.sql",
    "V0004__create_core_weather_forecasts.sql",
    "V0005__create_core_field_operations.sql",
    "V0006__create_read_field_snapshot.sql",
    "V0007__create_core_cadastro.sql",
    "V0008__add_product_and_equipment_to_operations.sql",
]


def test_applies_everything_once(db):
    assert migrate(db) == ALL
    assert migrate(db) == []

    with psycopg.connect(db) as conn:
        schemas = {r[0] for r in conn.execute("SELECT nspname FROM pg_namespace")}
        tables = {
            r[0]
            for r in conn.execute(
                "SELECT table_schema || '.' || table_name FROM information_schema.tables"
            )
        }
    assert {"raw", "core", "read"} <= schemas
    assert {
        "raw.open_meteo_events",
        "raw.field_events",
        "core.weather_forecasts",
        "core.field_operations",
        "read.field_snapshot",
        "core.producers",
        "core.producer_contacts",
        "core.producer_crops",
        "core.farms",
        "core.fields",
    } <= tables


@pytest.mark.parametrize("table", ["raw.open_meteo_events", "raw.field_events"])
def test_duplicate_idempotency_key_inserts_once(db, table):
    migrate(db)
    insert = f"""
        INSERT INTO {table} (idempotency_key, tenant_id, field_id, occurred_at, payload)
        VALUES ('k1', 't1', 'f1', now(), '{{}}')
        ON CONFLICT (idempotency_key) DO NOTHING
        RETURNING id
    """
    with psycopg.connect(db) as conn:
        assert conn.execute(insert).fetchone() is not None
        assert conn.execute(insert).fetchone() is None
        assert conn.execute(f"SELECT count(*) FROM {table}").fetchone() == (1,)


def test_refuses_edited_migration(db, tmp_path):
    shutil.copytree(MIGRATIONS_DIR, tmp_path, dirs_exist_ok=True)
    migrate(db, tmp_path)
    first = tmp_path / ALL[0]
    first.write_text(first.read_text() + "\nCREATE SCHEMA extra;\n")

    with pytest.raises(MigrationError, match="mudou depois de aplicada"):
        migrate(db, tmp_path)

    with psycopg.connect(db) as conn:
        assert conn.execute("SELECT 1 FROM pg_namespace WHERE nspname = 'extra'").fetchone() is None
