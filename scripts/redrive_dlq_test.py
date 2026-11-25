import pytest

from scripts.redrive_dlq import redrive

DLQ_ARN = "arn:aws:sqs:sa-east-1:000:events-dlq"


class FakeSQS:
    """Imita o StartMessageMoveTask: devolve os status em sequência a cada consulta."""

    def __init__(self, *statuses):
        self.statuses = list(statuses)
        self.started = []

    def get_queue_url(self, QueueName):
        return {"QueueUrl": f"http://sqs/{QueueName}"}

    def get_queue_attributes(self, QueueUrl, AttributeNames):
        return {"Attributes": {"QueueArn": DLQ_ARN}}

    def start_message_move_task(self, **kwargs):
        self.started.append(kwargs)
        return {"TaskHandle": "t-2"}

    def list_message_move_tasks(self, SourceArn):
        status = self.statuses.pop(0)
        old = {"TaskHandle": "t-1", "Status": "COMPLETED", "ApproximateNumberOfMessagesMoved": 9}
        new = {"TaskHandle": "t-2", "Status": status, "ApproximateNumberOfMessagesMoved": 2}
        return {"Results": [old, new]}


def test_moves_back_to_the_source_queue_and_waits(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda _: None)
    sqs = FakeSQS("RUNNING", "COMPLETED")

    assert redrive(sqs, "events-dlq") == 2  # conta a task nova, não a antiga
    assert sqs.started == [{"SourceArn": DLQ_ARN}]  # sem destino: volta para a origem


def test_failed_task_raises():
    with pytest.raises(RuntimeError, match="FAILED"):
        redrive(FakeSQS("FAILED"), "events-dlq")
