import time
from magicflow.libs.logging_service import LoggingService

logger = LoggingService().getLogger("dummy")
from magicflow.messaging import CommandMessage
from magicflow.jobs import jobs, Jobs
j = jobs()

@j.register("dummy_job")
def dummy_job(context: Jobs, cmd: CommandMessage):
    # get data from msg
    logger.debug('Doing dummy job msg = %s' % cmd)
    input_data = cmd.get_data()["input"]
    mr_id = input_data['mr_id']
    return {"mr_id:": mr_id}

@j.register("dummy_job2")
def dummy_job2(context: Jobs, cmd: CommandMessage):
    # get data from msg
    logger.debug('Doing dummy job2  msg = %s' % cmd)
    time.sleep(20)
    logger.debug('Completed dummy job2')
    return {"return": 2}
