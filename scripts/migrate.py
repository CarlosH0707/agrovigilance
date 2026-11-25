"""Aplica as migrations de `migrations/` em ordem (ADR-0009, ADR-0013).

Ferramenta de desenvolvimento/operação, fora do pacote do app.
Uso: uv run --env-file .env python scripts/migrate.py
"""

import hashlib
import os
import re
from dataclasses import dataclass
from pathlib import Path

import psycopg
from psycopg.conninfo import make_conninfo

MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"
NAME_PATTERN = re.compile(r"^V(\d{4})__[a-z0-9_]+\.sql$")
LOCK_ID = 73012026  # chave fixa do advisory lock: uma execução por vez


class MigrationError(Exception):
    pass


@dataclass(frozen=True)
class Migration:
    version: str
    name: str
    sql: str
    checksum: str


def discover(directory: Path) -> list[Migration]:
    migrations: dict[str, Migration] = {}
    for path in directory.glob("*.sql"):
        match = NAME_PATTERN.match(path.name)
        if not match:
            raise MigrationError(f"nome fora do padrão V<NNNN>__<nome>.sql: {path.name}")
        version = match.group(1)
        if version in migrations:
            raise MigrationError(
                f"versão {version} repetida: {migrations[version].name} e {path.name}"
            )
        sql = path.read_text(encoding="utf-8")
        checksum = hashlib.sha256(sql.encode()).hexdigest()
        migrations[version] = Migration(version, path.name, sql, checksum)
    return [migrations[v] for v in sorted(migrations)]


def pending(migrations: list[Migration], applied: dict[str, str]) -> list[Migration]:
    """Devolve o que falta aplicar; falha se uma migration aplicada mudou ou sumiu."""
    on_disk = {m.version: m for m in migrations}
    for version, checksum in applied.items():
        if version not in on_disk:
            raise MigrationError(f"migration {version} foi aplicada mas não está no disco")
        if on_disk[version].checksum != checksum:
            raise MigrationError(
                f"{on_disk[version].name} mudou depois de aplicada; crie uma migration nova"
            )
    return [m for m in migrations if m.version not in applied]


def migrate(conninfo: str, directory: Path = MIGRATIONS_DIR) -> list[str]:
    """Aplica as migrations pendentes e devolve os nomes aplicados."""
    migrations = discover(directory)
    done: list[str] = []
    with psycopg.connect(conninfo, autocommit=True) as conn:
        conn.execute("SELECT pg_advisory_lock(%s)", (LOCK_ID,))
        try:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS public.schema_migrations (
                       version text PRIMARY KEY,
                       checksum text NOT NULL,
                       applied_at timestamptz NOT NULL DEFAULT now()
                   )"""
            )
            rows = conn.execute("SELECT version, checksum FROM public.schema_migrations")
            for migration in pending(migrations, dict(rows.fetchall())):
                with conn.transaction():
                    conn.execute(migration.sql)
                    conn.execute(
                        "INSERT INTO public.schema_migrations (version, checksum) VALUES (%s, %s)",
                        (migration.version, migration.checksum),
                    )
                done.append(migration.name)
        finally:
            conn.execute("SELECT pg_advisory_unlock(%s)", (LOCK_ID,))
    return done


def conninfo_from_env() -> str:
    return make_conninfo(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=os.environ.get("POSTGRES_PORT", "5432"),
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
    )


if __name__ == "__main__":
    applied = migrate(conninfo_from_env())
    print("\n".join(f"aplicada: {name}" for name in applied) or "nada a aplicar")
