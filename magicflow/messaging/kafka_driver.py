from typing import Callable
from magicflow.config.config import settings
from magicflow.libs.logging_service import LoggingService
from magicflow.messaging.kafka_connect import KafkaConnect

logger = LoggingService().getLogger(__name__)

from magicflow.messaging.exceptions import QueueConnectionError, QueueAuthError

class KafkaDriver:
    def __init__(self, config: settings, queue: str):
        self._config = config
        self._queue = queue
        self._kafka_connect = KafkaConnect()
        self._running = True

    def publish_message(self, message: str) -> bool:
        try:
            result = self._kafka_connect.kafka_produce(self._queue, message)
            if result == 0:
                raise QueueConnectionError("Failed to publish message to Kafka")
            
            return True
        except Exception as e:
            logger.error(f"Failed to publish message to Kafka: {e}")
            raise QueueConnectionError(e)

    def consume_message(self, message_handler: Callable) -> bool:
        try:
            self._kafka_connect.kafka_consume(self._queue, message_handler)
            return True
        except Exception as e:
            logger.error(f"Failed to consume messages from Kafka: {str(e)}")
            return False

    def ack(self, tag: int) -> None:
        # In Kafka, we don't need to explicitly acknowledge messages
        # as we're using auto-commit configuration
        pass

    def close(self) -> None:
        self._running = False
        # Cleanup is handled by the Kafka consumer's close method 