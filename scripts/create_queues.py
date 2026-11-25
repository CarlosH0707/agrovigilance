"""Cria a fila de eventos e a DLQ no SQS (ADR-0003, ADR-0015).

Idempotente: rodar de novo não muda nada. Ferramenta fora do pacote do app.
Uso: uv run --env-file .env python scripts/create_queues.py
"""

import json

import boto3

from agrovigilance.infrastructure.queues.events.publisher import QUEUE_NAME

DLQ_NAME = f"{QUEUE_NAME}-dlq"
MAX_RECEIVE_COUNT = 3


def ensure_queues(sqs, queue_name: str = QUEUE_NAME, dlq_name: str = DLQ_NAME) -> str:
    """Cria a DLQ e a fila principal com redrive para ela; devolve a URL da principal."""
    dlq_url = sqs.create_queue(QueueName=dlq_name)["QueueUrl"]
    dlq_arn = sqs.get_queue_attributes(QueueUrl=dlq_url, AttributeNames=["QueueArn"])[
        "Attributes"
    ]["QueueArn"]
    redrive = {"deadLetterTargetArn": dlq_arn, "maxReceiveCount": str(MAX_RECEIVE_COUNT)}
    return sqs.create_queue(
        QueueName=queue_name, Attributes={"RedrivePolicy": json.dumps(redrive)}
    )["QueueUrl"]


if __name__ == "__main__":
    print(f"fila pronta: {ensure_queues(boto3.client('sqs'))}")
