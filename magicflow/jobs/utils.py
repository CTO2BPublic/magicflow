import json
from magicflow.messaging import CommandMessage

def validate_inputs(inputs: list, cmd: CommandMessage) -> list:
    """
    Validate inputs against schema
    :param inputs: inputs to validate
    :param cmd: command message
    :return: None if inputs are valid, dict with result and error messages
    """
    missing = []
    input = cmd.get_data()["input"]

    for key in inputs:
        if key not in input:
            missing.append(key)

    if len(missing) > 0:
      return {
          "result": "Missing inputs",
          "error": json.dumps({
              "message": "Missing inputs",
              "missing_inputs": missing
          }, indent=4)
      }
    return None

def wokflow_pause(result: str, parameters: dict = None, logs: str = None, error: str = None, timeout: int = 30) -> dict:
    return workflow_result(result, parameters=parameters, logs=logs, error=error, workflow_control={"pause": "true", "pause_seconds": 30})

def workflow_success(result: str, logs: str = None, error: str = None, parameters: dict = None) -> dict:
    return workflow_result(result, parameters=parameters, logs=logs, error=error)

def workflow_fail(result: str, logs: str = None, error: str = "Job failed") -> dict:
    return workflow_result(result, logs=logs, error=error, workflow_control={"abort": "true"})

def workflow_result(result: str, parameters: dict = None, logs: str = None, error: str = None, workflow_control: dict = None) -> dict:
    return {
        "result": result,
        "workflow_control": workflow_control,
        "parameters": parameters,
        "logs": logs,
        "error": error
    }
