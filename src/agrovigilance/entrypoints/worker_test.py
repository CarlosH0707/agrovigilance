from agrovigilance.entrypoints.worker import process_messages
from agrovigilance.infrastructure.queues.events.consumer import ReceivedMessage

OK = '{"source": "field_events", "event_id": "019ab000-0000-7000-8000-000000000001"}'
BOOM = '{"source": "open_meteo_events", "event_id": "019ab000-0000-7000-8000-000000000002"}'


class FakeConsumer:
    def __init__(self):
        self.deleted = []

    def delete(self, message):
        self.deleted.append(message.receipt_handle)


def failing(_event_id):
    raise RuntimeError("banco fora")


def test_deletes_only_what_succeeded():
    consumer = FakeConsumer()
    messages = [
        ReceivedMessage(OK, "r-ok"),
        ReceivedMessage(BOOM, "r-boom"),
        ReceivedMessage("lixo", "r-lixo"),
    ]
    handlers = {"field_events": lambda _: "processed", "open_meteo_events": failing}

    assert process_messages(messages, handlers, consumer) == 1
    assert consumer.deleted == ["r-ok"]  # as outras voltam para a fila e contam para a DLQ
