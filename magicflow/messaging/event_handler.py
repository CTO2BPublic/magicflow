import sys
from queue import Queue
from typing import Callable, TYPE_CHECKING, Any

from magicflow.config.config import settings

from magicflow.jobs import JobRunner, load_jobs

from magicflow.messaging import CommandMessage
from magicflow.messaging.base_processor import DefaultEventProcessor
from magicflow.messaging import EventMessage
from magicflow.messaging import TerminationMessage
from magicflow.messaging.exceptions import InvalidMessageFormat
from magicflow.messaging.exceptions import PermanentError

if TYPE_CHECKING:
    from magicflow.messaging.kafka_driver import KafkaDriver

from magicflow.libs.logging_service import LoggingService

logger = LoggingService().getLogger(__name__)

def _default_kafka_driver_factory(settings: Any) -> 'KafkaDriver':
    from magicflow.messaging.kafka_driver import KafkaDriver
    consume_topic = settings.get("kafka_consume_queue_topic")
    if not consume_topic:
        # Fallback or error if the setting is crucial and not found
        logger.error("'kafka_consume_queue_topic' not found in settings. Falling back to default or erroring.")
        # Decide on a robust fallback or raise a configuration error
        consume_topic = "cto2b.magicflow.workflows.worker.job" # Example fallback
    return KafkaDriver(config=settings, queue=consume_topic)


def _default_job_runner_factory(settings: Any) -> JobRunner:
    return JobRunner(settings)

class EventHandler(DefaultEventProcessor):

    def __init__(
        self,
        thread_id: int,
        name: str,
        internal_queue: Queue,
        settings: Any,
        kafka_driver_factory: Callable[[Any], 'KafkaDriver'] = _default_kafka_driver_factory,  
        job_runner_factory: Callable[[Any], JobRunner] = _default_job_runner_factory,
    ):
        super(EventHandler, self).__init__(thread_id, name, internal_queue, settings,
                                           kafka_driver_factory)
        self._job_runner = job_runner_factory(settings)

        load_jobs()

    def stop(self):
        super(EventHandler, self).stop()
        self._kafka_driver.close()
        self._internal_queue.put(TerminationMessage())

    def message_handler(self):
        receiver = self._kafka_driver
        internal_queue = self._internal_queue
        job_runner = self._job_runner

        def on_message(tag, body):
            logger.debug(f"Received message {tag} with body: {body}")
            try:
                # Issue with a command, which means we cannot generate a status event
                command = CommandMessage(body)
                status = "Completed"
                try:
                    response = job_runner.run(command)
                except Exception as e:
                    logger.error(f"Seems job failed to run: {str(e)}", exc_info=True)
                    response = dict({"error": f"Exception: {e}"})
                    status = "Error"
                try:
                    # Override status if workflow_control is present in a job output
                    if "workflow_control" in response and response["workflow_control"] is not None:
                        if "pause" in response["workflow_control"]:
                            status = "Sleep"
                    # Issue with a event, which means we cannot generate a status event
                    event = EventMessage(response, status, command)
                    internal_queue.put(event)
                except InvalidMessageFormat as e:
                    logger.warning(f"Invalid format for the event: {str(e)}", exc_info=True)
                    logger.warning(
                        "Removing message from queue, since permanently failed to send response")
            except PermanentError as e:
                logger.warning(f"Exception in message marshaling: {str(e)}", exc_info=True)
                logger.warning("Removing message from queue, since permanently failed")
                logger.debug(body)

            # In Kafka, we don't need to explicitly acknowledge messages
            # as we're using auto-commit configuration
            pass

        return on_message

    def run(self) -> None:
        if not self._kafka_driver.consume_message(self.message_handler()):
            logger.error("Seems Kafka got an issue, die!!")
            sys.exit(255)

        logger.info("Stopping EventHandler")
