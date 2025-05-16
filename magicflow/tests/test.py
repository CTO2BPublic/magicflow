# -*- coding: utf-8 -*-
import time
import base64

import requests
from dynaconf import Dynaconf
import yaml
from magicflow.config import settings
import gitlab
from xml.dom.expatbuilder import Namespaces


from magicflow.messaging import CommandMessage
from magicflow.libs.yaml_dumper import CustomDumper
from magicflow.libs.gitlab_service import GitlabDriver
from loguru import logger


msg = {
	"id": "b8e4e91f-3a71-46af-9f91-f01999c80734",
	"created_at": "0001-01-01T00:00:00Z",
	"updated_at": "0001-01-01T00:00:00Z",
	"attributes": {
		"source": "magicflow-controller",
		"type": "job-input",
		"date": "2022-05-05T10:26:54.99872265Z"
	},
	"message": "",
	"data": {
		"created_at": "2022-05-05T10:26:10.785485Z",
		"input": {
			"from_jobs": [
				1
			],
			"mr_id": "1121",
            "project_id": "25047365"
		},
		"job_id": "66288897-7c32-44ba-9d38-0f8aa1ba944a",
		"name": "dummy_job",
		"order": 3,
		"output": {
			"error": {}
		},
		"status": "New",
		"updated_at": "2022-05-05T10:26:54.991202059Z",
		"workflow_id": "d2981e4e-b0fc-46be-90ac-4c5b17b1cb0b"
	}
}


class Jobs:

    def __init__(self, config: Dynaconf):
        self._config = config
        self.gitlab_api_token = self._config.get('gitlab_api_token')

    def check_approval(self, cmd: CommandMessage):
        try:
            assert cmd.get_data()["mr_id"]
            mr_id = cmd.get_data()["mr_id"]
            assert cmd.get_data()["project_id"]
            project_id = cmd.get_data()["project_id"]

            gl = GitlabDriver(self.gitlab_api_token, project_id)
            approver_list = gl.check_approval(mr_id)
            return {"approved": True, "approvers": approver_list}

        except AssertionError:
            logger.error('Missing input parameters')
            return False

if __name__ == '__main__':
    j = Jobs(settings).check_approval(msg)
    print(j)
