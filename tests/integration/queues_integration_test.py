"""A fila e a DLQ funcionam de verdade no Floci (ADR-0003, ADR-0015)."""

import json
import uuid

import pytest

from scripts.create_queues import MAX_RECEIVE_COUNT, ensure_queues

pytestmark = pytest.mark.integration


@pytest.fixture
def names():
    suffix = uuid.uuid4().hex[:8]
    return f"events-{suffix}", f"events-{suffix}-dlq"


def test_ensure_queues_is_idempotent_and_sets_redrive(sqs, names):
    queue, dlq = names

    url = ensure_queues(sqs, queue, dlq)

    assert ensure_queues(sqs, queue, dlq) == url
    dlq_arn = sqs.get_queue_attributes(
        QueueUrl=sqs.get_queue_url(QueueName=dlq)["QueueUrl"], AttributeNames=["QueueArn"]
    )["Attributes"]["QueueArn"]
    attrs = sqs.get_queue_attributes(QueueUrl=url, AttributeNames=["RedrivePolicy"])
    redrive = json.loads(attrs["Attributes"]["RedrivePolicy"])
    assert redrive["deadLetterTargetArn"] == dlq_arn
    assert int(redrive["maxReceiveCount"]) == MAX_RECEIVE_COUNT


def test_message_goes_to_dlq_after_max_receives(sqs, names):
    queue, dlq = names
    url = ensure_queues(sqs, queue, dlq)
    dlq_url = sqs.get_queue_url(QueueName=dlq)["QueueUrl"]
    sqs.send_message(QueueUrl=url, MessageBody="poison")

    for _ in range(MAX_RECEIVE_COUNT):  # recebe e "falha" (não deleta)
        got = sqs.receive_message(QueueUrl=url, VisibilityTimeout=0, WaitTimeSeconds=1)
        assert [m["Body"] for m in got.get("Messages", [])] == ["poison"]

    again = sqs.receive_message(QueueUrl=url, VisibilityTimeout=0, WaitTimeSeconds=1)
    assert again.get("Messages", []) == []
    dead = sqs.receive_message(QueueUrl=dlq_url, WaitTimeSeconds=1)
    assert [m["Body"] for m in dead.get("Messages", [])] == ["poison"]
