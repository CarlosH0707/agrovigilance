"""Postgres descartável para testes de integração (ADR-0014)."""

import uuid

import psycopg
import pytest
from psycopg.conninfo import conninfo_to_dict, make_conninfo
from testcontainers.community.postgres import PostgresContainer


@pytest.fixture(scope="session")
def pg_server():
    """Sobe um postgres:19.0 por execução; o testcontainers remove no fim."""
    with PostgresContainer("postgres:19.0", driver=None) as container:
        yield container.get_connection_url()


@pytest.fixture
def db(pg_server):
    """Banco novo e vazio para cada teste; devolve o conninfo dele."""
    name = f"test_{uuid.uuid4().hex}"
    with psycopg.connect(pg_server, autocommit=True) as admin:
        admin.execute(f'CREATE DATABASE "{name}"')
    yield make_conninfo(**{**conninfo_to_dict(pg_server), "dbname": name})
    with psycopg.connect(pg_server, autocommit=True) as admin:
        admin.execute(f'DROP DATABASE "{name}" WITH (FORCE)')
