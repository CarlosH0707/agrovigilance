"""Postgres e Floci descartáveis para testes de integração (ADR-0014, ADR-0015)."""

import time
import uuid

import boto3
import psycopg
import pytest
from botocore.exceptions import BotoCoreError, ClientError
from psycopg.conninfo import conninfo_to_dict, make_conninfo
from testcontainers.community.postgres import PostgresContainer
from testcontainers.core.container import DockerContainer

from scripts.migrate import migrate


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


FAKE_AWS = {
    "region_name": "sa-east-1",
    "aws_access_key_id": "test",
    "aws_secret_access_key": "test",
}


@pytest.fixture(scope="session")
def floci_url():
    """Sobe um Floci descartável por execução (ADR-0015)."""
    with DockerContainer("floci/floci:2.5.0").with_exposed_ports(4566) as container:
        url = f"http://{container.get_container_host_ip()}:{container.get_exposed_port(4566)}"
        _wait_until_up(boto3.client("sqs", endpoint_url=url, **FAKE_AWS))
        yield url


@pytest.fixture
def sqs(floci_url):
    return boto3.client("sqs", endpoint_url=floci_url, **FAKE_AWS)


def _wait_until_up(client, timeout=30.0):
    deadline = time.monotonic() + timeout
    while True:
        try:
            client.list_queues()
            return
        except BotoCoreError, ClientError:
            if time.monotonic() > deadline:
                raise
            time.sleep(0.5)


@pytest.fixture
def tenant(db):
    """Banco migrado com produtor, propriedade e talhão `f1` (ADR-0026); devolve o tenant_id."""
    migrate(db)
    with psycopg.connect(db, autocommit=True) as conn:
        producer_id = conn.execute(
            "INSERT INTO core.producers (name) VALUES ('Teste') RETURNING id"
        ).fetchone()[0]
        farm_id = conn.execute(
            "INSERT INTO core.farms (producer_id, name, region, timezone)"
            " VALUES (%s, 'Sede', 'ES', 'America/Sao_Paulo') RETURNING id",
            (producer_id,),
        ).fetchone()[0]
        conn.execute(
            "INSERT INTO core.fields (producer_id, field_id, farm_id, name, crop, latitude, longitude)"
            " VALUES (%s, %s, %s, 'Café', 'cafe', -19.0, -40.0)",
            (producer_id, "f1", farm_id),
        )
    return str(producer_id)
