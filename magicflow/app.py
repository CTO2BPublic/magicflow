import os, sys
import signal
from queue import Queue
from magicflow.libs.logging_service import LoggingService
from magicflow.libs.metadata import Metadata
from magicflow.config.config import settings
from magicflow.messaging.event_dispatcher import EventDispatcher
from magicflow.messaging.event_handler import EventHandler

logger = LoggingService().getLogger(__name__)

queue = Queue()
handler = EventHandler(1, "main_worker_handler", queue, settings)
dispatcher = EventDispatcher(1, "main_worker_dispatcher", queue, settings)

def signal_handler(s,h):
    logger.info("Completing handler")
    handler.alive = False
    dispatcher.alive = False

    handler.stop()
    handler.join()
    logger.info("Completing dispatcher")
    dispatcher.stop()
    dispatcher.join()


def event_handler():
    logger.info("Starting event handler")
    try:
        handler.start()
        dispatcher.start()
    except KeyboardInterrupt as e:
		# Set the alive attribute to false
        handler.alive = False
        dispatcher.alive = False
		# Block until child thread is joined back to the parent
        handler.stop()
        handler.join()
        dispatcher.stop()
        dispatcher.join()
		# Exit with error code
        sys.exit(e)


def read_token_file(token_file):
    if os.path.isfile(token_file):
        with open(token_file, encoding='utf8') as f:
            content = f.read()
            if not content:
                raise Exception("Token file exists but empty.")
            return content
    else:
        logger.warning('AGENT WARNING: unable to read token file')
        return "localtokenrun"


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

if __name__ == '__main__':
    os.environ['APP_TOKEN'] = read_token_file(settings.token_file)

    meta = Metadata.get_instance(
        stage = os.environ.get('STAGE'),
        environment = os.environ.get('ENVIRONMENT'),
        cloud = os.environ.get('CLOUD')
    )



    event_handler()
