import json
import threading
from abc import ABC
from queue import Queue
from typing import Callable
from magicflow.libs.logging_service import LoggingService

logger = LoggingService().getLogger("messaging")

from jsonschema import ValidationError
from jsonschema import validate

from magicflow.messaging.exceptions import InvalidMessageFormat

# Move DefaultEventProcessor to a separate file to avoid circular imports
from magicflow.messaging.base_processor import DefaultEventProcessor

GenericCommandSchema = {
    "type": "object",
    "properties": {
        "id": {
            "type": "string"
        },
        "created_at": {
            "type": "string"
        },
        "updated_at": {
            "type": "string"
        },
        "attributes": {
            "type": "object",
            "properties": {
                "source": {
                    "type": "string"
                },
                "type": {
                    "type": "string"
                },
                "date": {
                    "type": "string"
                }
            },
            "required": ["source", "type", "date"]
        },
        "message": {
            "type": "string"
        },
        "data": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string"
                },
                "created_at": {
                    "type": "string"
                },
                "updated_at": {
                    "type": "string"
                },
                "input": {
                    "type": "object"
                },
                "workflow_id": {
                    "type": "string"
                },
                "status": {
                    "type": "string"
                },
                "job_id": {
                    "type": "string"
                }
            },
            "required": ["name", "input", "workflow_id", "job_id"]
        }
    },
    "required": ["id", "attributes", "data"]
}

GenericEventSchema = {
    "type": "object",
    "properties": {
        "id": {
            "type": "string"
        },
        "created_at": {
            "type": "string"
        },
        "updated_at": {
            "type": "string"
        },
        "attributes": {
            "type": "object",
            "properties": {
                "source": {
                    "type": "string"
                },
                "type": {
                    "type": "string"
                },
                "date": {
                    "type": "string"
                }
            },
            "required": ["source", "type", "date"]
        },
        "message": {
            "type": "string"
        },
        "data": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string"
                },
                "input": {
                    "type": "object"
                },
                "output": {
                    "type": "object"
                },
                "workflow_id": {
                    "type": "string"
                },
                "job_id": {
                    "type": "string"
                },
                "status": {
                    "type": "string"
                }
            },
            "required": ["name", "input", "output", "workflow_id", "job_id", "status"]
        }
    },
    "required": ["id", "attributes", "data"]
}

class CommandMessage:
    def __init__(self, body: str, schema=None):
        if schema is None:
            schema = GenericCommandSchema
        try:
            self._body = json.loads(body)
            self._raw_body = body
            self._schema = schema
        except ValueError as e:
            logger.error("Failed to convert Command message to JSON", exc_info=1)
            logger.debug("Body of a message: %s" % body)
            raise InvalidMessageFormat(e)

        self._validate()

    def _validate(self):
        try:
            validate(self._body, self._schema)
        except ValidationError as e:
            logger.error("Failed to validate command against schema", exc_info=1)
            raise InvalidMessageFormat(e)

    def get_attributes(self) -> dict:
        return self._body['attributes']

    def get_id(self) -> str:
        return self._body['id']

    def get_data(self) -> dict:
        return self._body['data']

    def get_body(self) -> dict:
        return dict(self._body)

class EventMessage:
    def __init__(self, output: dict, status: str, command: CommandMessage, schema=None):
        if schema is None:
            schema = GenericEventSchema
        self._schema = schema

        self._body = command.get_body()

        if "output" not in self._body["data"]:
            self._body["data"]["output"] = output
        else:
            self._body["data"]["output"].update(output)

        self._body["data"]["status"] = status
        self._validate()

    def _validate(self):
        try:
            validate(self._body, self._schema)
        except ValidationError as e:
            logger.error("Failed to validate event against schema", exc_info=1)
            raise InvalidMessageFormat(e)

    def to_json(self):
        return json.dumps(self._body)

class TerminationMessage:
    pass
