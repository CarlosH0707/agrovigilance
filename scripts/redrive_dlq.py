"""Devolve as mensagens da DLQ para a fila de origem (ADR-0023).

Usa o redrive nativo do SQS (StartMessageMoveTask): sem destino, cada mensagem volta
para a fila de onde caiu. Rode depois de corrigir a causa da falha.
Uso: uv run --env-file .env python scripts/redrive_dlq.py
"""

import time

import boto3

from scripts.create_queues import DLQ_NAME


def redrive(sqs, dlq_name: str = DLQ_NAME, timeout: float = 60.0) -> int:
    """Move tudo da DLQ de volta e espera terminar; devolve quantas mensagens moveu."""
    dlq_url = sqs.get_queue_url(QueueName=dlq_name)["QueueUrl"]
    dlq_arn = sqs.get_queue_attributes(QueueUrl=dlq_url, AttributeNames=["QueueArn"])["Attributes"][
        "QueueArn"
    ]
    handle = sqs.start_message_move_task(SourceArn=dlq_arn)["TaskHandle"]
    deadline = time.monotonic() + timeout
    while True:
        task = next(
            t
            for t in sqs.list_message_move_tasks(SourceArn=dlq_arn)["Results"]
            if t["TaskHandle"] == handle
        )
        if task["Status"] == "COMPLETED":
            return task.get("ApproximateNumberOfMessagesMoved", 0)
        if task["Status"] in ("FAILED", "CANCELLED"):
            raise RuntimeError(f"redrive {task['Status']}: {task.get('FailureReason', '?')}")
        if time.monotonic() > deadline:
            raise TimeoutError(f"redrive ainda {task['Status']} após {timeout}s")
        time.sleep(0.5)


if __name__ == "__main__":
    print(f"mensagens devolvidas: {redrive(boto3.client('sqs'))}")
