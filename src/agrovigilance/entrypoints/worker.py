"""Worker: consome agrovigilance-events em loop com long polling (ADR-0021).

Uso: uv run --env-file .env python -m agrovigilance.entrypoints.worker
"""

import logging
import signal
import threading
from collections.abc import Mapping
from functools import partial

import boto3
import psycopg

from agrovigilance.application.process_event import (
    Handler,
    handle,
    process_field_operation,
    process_weather,
)
from agrovigilance.infrastructure.database.connection import conninfo_from_env
from agrovigilance.infrastructure.database.core.field_operations.repository import (
    FieldOperationRepository,
)
from agrovigilance.infrastructure.database.core.weather_forecasts.repository import (
    WeatherForecastRepository,
)
from agrovigilance.infrastructure.database.raw.field_events.repository import FieldEventRepository
from agrovigilance.infrastructure.database.raw.open_meteo_events.repository import (
    OpenMeteoEventRepository,
)
from agrovigilance.infrastructure.database.read.field_snapshot.repository import (
    FieldSnapshotRepository,
)
from agrovigilance.infrastructure.queues.events.consumer import EventsConsumer, ReceivedMessage
from agrovigilance.infrastructure.queues.events.publisher import QUEUE_NAME

log = logging.getLogger(__name__)


def handlers_for(conn: psycopg.Connection) -> dict[str, Handler]:
    snapshot = FieldSnapshotRepository(conn)
    return {
        "open_meteo_events": partial(
            process_weather,
            raw=OpenMeteoEventRepository(conn),
            core=WeatherForecastRepository(conn),
            snapshot=snapshot,
        ),
        "field_events": partial(
            process_field_operation,
            raw=FieldEventRepository(conn),
            core=FieldOperationRepository(conn),
            snapshot=snapshot,
        ),
    }


def process_messages(
    messages: list[ReceivedMessage], handlers: Mapping[str, Handler], consumer
) -> int:
    """Apaga só o que deu certo; o resto volta à fila e, na 3ª falha, vai para a DLQ."""
    done = 0
    for message in messages:
        try:
            status = handle(message.body, handlers)
        except Exception:
            log.exception("falha ao processar a mensagem; ela volta para a fila")
            continue
        consumer.delete(message)
        log.info("mensagem %s", status)
        done += 1
    return done


def process_once(consumer: EventsConsumer, conninfo: str) -> int:
    """Um ciclo: espera mensagens (long polling), processa e apaga as que deram certo."""
    messages = consumer.receive()
    if not messages:
        return 0
    # Conexão por ciclo: se o banco cair e voltar, o próximo ciclo se recupera sozinho.
    with psycopg.connect(conninfo, autocommit=True) as conn:
        return process_messages(messages, handlers_for(conn), consumer)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    stop = threading.Event()
    for sig in (signal.SIGTERM, signal.SIGINT):
        # Termina o ciclo atual e sai; o pior caso é esperar o long polling (20 s).
        signal.signal(sig, lambda *_: stop.set())

    sqs = boto3.client("sqs")
    consumer = EventsConsumer(sqs, sqs.get_queue_url(QueueName=QUEUE_NAME)["QueueUrl"])
    conninfo = conninfo_from_env()
    log.info("worker ouvindo %s", QUEUE_NAME)
    while not stop.is_set():
        try:
            process_once(consumer, conninfo)
        except Exception:
            # Banco ou fila fora: as mensagens não apagadas voltam sozinhas (e vão para a DLQ
            # na 3ª vez). Espera um pouco para não girar em falso e tenta de novo.
            log.exception("ciclo falhou; tentando de novo")
            stop.wait(5)
    log.info("worker encerrado")


if __name__ == "__main__":
    main()
