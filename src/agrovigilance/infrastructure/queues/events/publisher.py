"""Publica na fila agrovigilance-events (ADR-0003)."""

import json
from typing import Any

QUEUE_NAME = "agrovigilance-events"
DLQ_NAME = f"{QUEUE_NAME}-dlq"


class EventsPublisher:
    def __init__(self, sqs, queue_url: str):
        self.sqs = sqs
        self.queue_url = queue_url

    def publish(self, message: dict[str, Any]) -> None:
        self.sqs.send_message(QueueUrl=self.queue_url, MessageBody=json.dumps(message))
