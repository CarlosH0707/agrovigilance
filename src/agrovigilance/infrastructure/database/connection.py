"""Conexão com o Postgres a partir do ambiente."""

import os

from psycopg.conninfo import make_conninfo


def conninfo_from_env() -> str:
    return make_conninfo(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=os.environ.get("POSTGRES_PORT", "5432"),
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
    )
