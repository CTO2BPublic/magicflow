import zlib
import yaml
import json

from magicflow.messaging import CommandMessage
from magicflow.jobs import jobs, Jobs
from magicflow.jobs.utils import validate_inputs, workflow_success, workflow_fail
from magicflow.libs.logging_service import LoggingService

logger = LoggingService().getLogger(__name__)

j = jobs()

@j.register("ssm_list_all")
def ssm_list_all(context: Jobs, cmd: CommandMessage):

    metadata = context.metadata()

    if metadata.validate(["cloud", "stage", "environment"]):
        return workflow_fail(**metadata.validate(["cloud", "stage", "environment"]))

    cloud = metadata.get("cloud")
    stage = metadata.get("stage")
    environment = metadata.get("environment")

    parameters = []
    if cloud == "aws":
        logger.debug("Working with AWS SSM")
        from magicflow.libs.ssm.aws import list_parameters
        parameters = list_parameters(stage, environment)
        if not parameters or len(parameters) == 0:
            return workflow_success("No secrets found")
    elif cloud == "gcp":
        logger.debug("Working with GCP SSM")
        from magicflow.libs.ssm.gcp import list_parameters
        parameters = list_parameters(stage, environment)
        if not parameters or len(parameters) == 0:
            return workflow_success("No secrets found")
    else:
        return workflow_fail(f'Cloud {cloud} not supported')

    logger.debug(f"Secrets found: {parameters}")

    return workflow_success("Secrets found", logs=json.dumps(parameters, indent=4))


@j.register("ssm_list")
def ssm_list(context: Jobs, cmd: CommandMessage):

    metadata = context.metadata()

    if metadata.validate(["cloud", "stage", "environment"]):
        return workflow_fail(**metadata.validate(["cloud", "stage", "environment"]))

    if validate_inputs(["namespace", "name"], cmd):
        return workflow_fail(**validate_inputs(["namespace", "name"], cmd))

    namespace = cmd.get_data()["input"]["namespace"]
    name = cmd.get_data()["input"]["name"]

    cloud = metadata.get("cloud")
    stage = metadata.get("stage")
    environment = metadata.get("environment")

    parameters = {}
    if cloud == "aws":
        logger.debug("Working with AWS SSM")
        from magicflow.libs.ssm.aws import get_parameter
        parameters = get_parameter(stage, environment, namespace, name)
        if not parameters or len(parameters) == 0:
            return workflow_success("No secrets found")
    elif cloud == "gcp":
        logger.debug("Working with GCP SSM")
        from magicflow.libs.ssm.gcp import get_parameter
        parameters = get_parameter(stage, environment, namespace, name)
        if not parameters or len(parameters) == 0:
            return workflow_success("No secrets found")
    else:
        return workflow_fail(f'Cloud {cloud} not supported')

    logger.debug(f"Secrets found: {parameters}")
    output = {}
    for key, value in parameters.items():
        output[key] = f'crc32({zlib.crc32(str(value).encode()):x})'

    return workflow_success("Secrets found", logs=json.dumps(output, indent=4))

@j.register("ssm_update")
def ssm_update(context: Jobs, cmd: CommandMessage):
    metadata = context.metadata()

    if metadata.validate(["cloud", "stage", "environment"]):
        return workflow_fail(**metadata.validate(["cloud", "stage", "environment"]))

    if validate_inputs(["namespace", "name", "values"], cmd):
        return workflow_fail(**validate_inputs(["namespace", "name", "values"], cmd))

    namespace = cmd.get_data()["input"]["namespace"]
    name = cmd.get_data()["input"]["name"]
    values = yaml.safe_load(cmd.get_data()["input"]["values"])

    cloud = metadata.get("cloud")
    stage = metadata.get("stage")
    environment = metadata.get("environment")

    if cloud == "aws":
        from magicflow.libs.ssm.aws import update_parameter
        update_parameter(values, stage, environment, namespace, name)
    elif cloud == "gcp":
        from magicflow.libs.ssm.gcp import update_parameter
        update_parameter(values, stage, environment, namespace, name)
    else:
        return workflow_fail(f'Cloud {cloud} not supported')
    output = {}
    for key, value in values.items():
        output[key] = f'crc32({zlib.crc32(str(value).encode()):x})'

    return workflow_success("Secret updated", logs=json.dumps(output, indent=4))
