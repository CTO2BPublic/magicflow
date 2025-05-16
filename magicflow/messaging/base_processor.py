import threading
from abc import ABC
from queue import Queue
from typing import Callable, TYPE_CHECKING, Any
from magicflow.config.config import settings

if TYPE_CHECKING:
    from magicflow.messaging.kafka_driver import KafkaDriver

class DefaultEventProcessor(ABC, threading.Thread):
    _kafka_driver: 'KafkaDriver'

    def __init__(
        self,
        thread_id: int,
        name: str,
        internal_queue: Queue,
        settings: Any,
        kafka_driver_factory: Callable[[Any], 'KafkaDriver'],
    ):
        threading.Thread.__init__(self)
        self._settings = settings
        self.thread_id = thread_id
        self.name = name
        self._internal_queue = internal_queue

        self._kafka_driver = kafka_driver_factory(settings)

        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()
