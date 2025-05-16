from unittest.mock import MagicMock
from unittest.mock import patch
from magicflow.jobs import Jobs
from magicflow.messaging import CommandMessage
from magicflow.libs.gitlab_service import GitlabDriver
from magicflow.config.config import settings
from typing import Any
def mocked_requests_get_factory(url, response):

    def mocked_requests_get(*args, **kwargs):

        class MockResponse:

            def __init__(self, json_data, status_code):
                self.json_data = json_data
                self.status_code = status_code

            def json(self):
                return self.json_data

        print(args)
        if args[0] == url:
            return MockResponse(response, 200)

        return MockResponse({}, 404)

    return mocked_requests_get


class TestJobs:
    _settings: Any = None
    _jobs: Jobs = None
    _cmd_data: dict = None

    @classmethod
    def setup_class(cls):
        cls._settings = MagicMock(spec="magicflow.config.config.settings")

        TestJobs._settings.get = MagicMock(
            side_effect=lambda value: "http://test/service" if value == "controller_uri" else value)

        cls._jobs = Jobs(config=cls._settings)
        cls._cmd_data = MagicMock(
            return_value={
                "input": {
                    "environment": "development",
                    "stage": "dev",
                    "namespace": "test",
                    "instance": "mock",
                    "service": "mysql"
                }
            })

    @patch("magicflow.messaging.CommandMessage")
    def test_check_environment_exists_not_exists(self, cmd: CommandMessage):
        cmd.get_data = TestJobs._cmd_data

        json_return_data = [
            {
                "Metadata": {
                    "Environment": "development2",
                    "Stage": "dev",
                    "Namespace": "test",
                    "Instance": "mock",
                },
            },
            {
                "Metadata": {
                    "Environment": "development3",
                    "Stage": "dev",
                    "Namespace": "test",
                    "Instance": "mock",
                },
            },
        ]

        with patch("requests.get",
                   side_effect=mocked_requests_get_factory("http://test/service",
                                                           json_return_data)):
            response = TestJobs._jobs.check_environment_exists(cmd)
            assert response["environment_exists"] is False

    @patch("magicflow.messaging.CommandMessage")
    def test_check_environment_exists_does_exists(self, cmd: CommandMessage):
        cmd.get_data = TestJobs._cmd_data

        json_return_data = [
            {
                "Metadata": {
                    "Environment": "development",
                    "Stage": "dev",
                    "Namespace": "test",
                    "Instance": "mock",
                },
            },
            {
                "Metadata": {
                    "Environment": "development2",
                    "Stage": "dev",
                    "Namespace": "test",
                    "Instance": "mock",
                },
            },
        ]

        with patch("requests.get",
                   side_effect=mocked_requests_get_factory("http://test/service",
                                                           json_return_data)):
            response = TestJobs._jobs.check_environment_exists(cmd)
            assert response["environment_exists"] is True

