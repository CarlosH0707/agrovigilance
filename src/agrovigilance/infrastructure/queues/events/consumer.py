"""Lê e apaga mensagens da fila agrovigilance-events (ADR-0003, ADR-0021)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ReceivedMessage:
    body: str
    receipt_handle: str


class EventsConsumer:
    def __init__(self, sqs, queue_url: str, wait_seconds: int = 20):
        self.sqs = sqs
        self.queue_url = queue_url
        self.wait_seconds = wait_seconds  # long polling: espera chegar algo em vez de girar

    def receive(self) -> list[ReceivedMessage]:
        got = self.sqs.receive_message(
            QueueUrl=self.queue_url, MaxNumberOfMessages=10, WaitTimeSeconds=self.wait_seconds
        )
        return [ReceivedMessage(m["Body"], m["ReceiptHandle"]) for m in got.get("Messages", [])]

    def delete(self, message: ReceivedMessage) -> None:
        self.sqs.delete_message(QueueUrl=self.queue_url, ReceiptHandle=message.receipt_handle)
