import sys
from queue import Queue
from typing import Callable, TYPE_CHECKING, Any
from magicflow.config.config import settings
from magicflow.libs.logging_service import LoggingService

logger = LoggingService().getLogger(__name__)

from magicflow.messaging.base_processor import DefaultEventProcessor
from magicflow.messaging import EventMessage
from magicflow.messaging import TerminationMessage

if TYPE_CHECKING:
    from magicflow.messaging.kafka_driver import KafkaDriver

def _default_kafka_driver_factory(settings: Any) -> 'KafkaDriver':
    from magicflow.messaging.kafka_driver import KafkaDriver
    # This dispatcher publishes events, so it needs the report/events topic.
    publish_topic = settings.get("kafka_report_queue_topic") 
    if not publish_topic:
        logger.error("'kafka_report_queue_topic' not found in settings. Falling back or erroring.")
        # Decide on a robust fallback or raise a configuration error
        publish_topic = "cto2b.magicflow.events" # Example fallback, ensure this is the correct topic for dispatched events
    return KafkaDriver(config=settings, queue=publish_topic)


class EventDispatcher(DefaultEventProcessor):

    def __init__(
        self,
        thread_id: int,
        name: str,
        internal_queue: Queue,
        settings: Any,
        kafka_driver_factory: Callable[[Any], 'KafkaDriver'] = _default_kafka_driver_factory,  
    ):
        super(EventDispatcher, self).__init__(thread_id, name, internal_queue, settings,
                                              kafka_driver_factory)

    def run(self) -> None:
        while not self.stopped():
            response = self._internal_queue.get()
            if isinstance(response, TerminationMessage):
                self.stop()
            elif isinstance(response, EventMessage):
                try:
                    self._kafka_driver.publish_message(response.to_json())
                except Exception:
                    logger.error("Seems Kafka got an issue, die!!", exc_info=1)
                    sys.exit(255)
            else:
                logger.error(f"Dispatcher received unknown message type: {response}")

        logger.info("Stopping EventDispatcher")
