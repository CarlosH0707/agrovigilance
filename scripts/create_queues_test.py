import json

from scripts.create_queues import DLQ_NAME, QUEUE_NAME, ensure_queues


class FakeSQS:
    """Imita o CreateQueue do SQS: mesmo nome e atributos devolve a mesma fila."""

    def __init__(self):
        self.queues: dict[str, dict] = {}
        self.created: list[str] = []

    def create_queue(self, QueueName, Attributes=None):
        attributes = Attributes or {}
        if QueueName in self.queues:
            assert self.queues[QueueName] == attributes, "atributos diferentes"
        else:
            self.queues[QueueName] = attributes
            self.created.append(QueueName)
        return {"QueueUrl": f"http://sqs/{QueueName}"}

    def get_queue_attributes(self, QueueUrl, AttributeNames):
        name = QueueUrl.rsplit("/", 1)[1]
        return {"Attributes": {"QueueArn": f"arn:aws:sqs:sa-east-1:000:{name}"}}


def test_creates_dlq_first_and_redrives_to_it():
    sqs = FakeSQS()

    url = ensure_queues(sqs)

    assert url == f"http://sqs/{QUEUE_NAME}"
    assert sqs.created == [DLQ_NAME, QUEUE_NAME]
    redrive = json.loads(sqs.queues[QUEUE_NAME]["RedrivePolicy"])
    assert redrive == {
        "deadLetterTargetArn": f"arn:aws:sqs:sa-east-1:000:{DLQ_NAME}",
        "maxReceiveCount": "3",
    }


def test_running_twice_is_harmless():
    sqs = FakeSQS()

    assert ensure_queues(sqs) == ensure_queues(sqs)
    assert sqs.created == [DLQ_NAME, QUEUE_NAME]
