# import yaml
import time, os, importlib
# import gitlab
from magicflow.config.config import settings
from magicflow.messaging import CommandMessage
from magicflow.libs.logging_service import LoggingService
from magicflow.libs.metadata import Metadata

logger = LoggingService().getLogger(__name__)

_j = None

def jobs():
    global _j
    if _j is None:
        _j = Jobs()
    return _j

def load_jobs():
    logger.debug("Starting to load jobs in %s" % os.path.dirname(__file__))
    lib_dir = os.path.join(os.path.dirname(__file__), "lib")
    
    # Filter for only .py files and exclude __pycache__
    python_files = [f for f in os.listdir(lib_dir) 
                   if f.endswith('.py') and not f.startswith('__')]
    
    for file in python_files:
        mod_name = file[:-3]  # Remove .py extension
        logger.debug(f"Loading jobs {mod_name}")
        try:
            importlib.import_module('.lib.' + mod_name, package=__name__)
        except ImportError:
            logger.opt(exception=True).error(f"Error importing job {mod_name}")

class JobRunner:
    def __init__(self, config: settings):
        self._config = config
        jobs().configure(config)

    def run(self, cmd: CommandMessage) -> dict:
        logger.debug("Got command with id %s" % cmd.get_id())
        job_name = cmd.get_data()['name']

        # Dynamically execute the method based on the job_name
        return jobs().execute(job_name, cmd)

class Jobs:
    _config: settings
    _jobs = {}

    def __init__(self, config: settings = None):
        self._config = config

    def configure(self, config: settings):
        logger.debug("Configuring jobs")
        self._config = config
        return self

    def config(self):
        return self._config

    def has(self, name):
        return name in self._jobs

    def metadata(self):
        return Metadata.get_instance()

    def register(self, name):
        logger.debug(f"Registering job {name}")
        def decorate(f):
            self._jobs[name] = f
            return f
        return decorate

    def execute(self, name, cmd):
        if name in self._jobs:
            return self._jobs[name](self, cmd)
        else:
            raise Exception("Job not found")
