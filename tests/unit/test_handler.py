# import json

import pytest

from git_lfs_aws_lambda.handler import Handler
from git_lfs_aws_lambda.lfs_error import LfsError
from ..fake_lambda_context import FakeLambdaContext


@pytest.fixture()
def given_event():
    return {
        "body": '{"test": "data"}'
    }


@pytest.fixture()
def given_context():
    return FakeLambdaContext()


class TestHandler(object):

    def test_valid_request(self, mocker, given_event, given_context):
        handler = Handler()

        mocker.patch('git_lfs_aws_lambda.handler.Handler.process').return_value = "expected"

        response = handler.handle(given_event, given_context)

        assert response == {
            "statusCode": 200,
            "headers": {"content-type": "application/json"},
            "body": '"expected"'
        }

    def test_should_wrap_known_erros(self, mocker, given_event, given_context):
        handler = Handler()

        mocker.patch('git_lfs_aws_lambda.handler.Handler.process').side_effect = LfsError(111, "testErr")
        mocker.patch('git_lfs_aws_lambda.handler.Handler.get_doc_url').side_effect = lambda code: f"doc for {code}"

        response = handler.handle(given_event, given_context)

        assert response == {
            "statusCode": 111,
            "headers": {"content-type": "application/json"},
            "body": '{"request_id": "testRequestId", "documentation_url": "doc for 111", "message": "testErr"}'
        }

    def test_should_500_unknown_errors(self, mocker, given_event, given_context):
        handler = Handler()

        mocker.patch('git_lfs_aws_lambda.handler.Handler.process').side_effect = Exception("Boom")

        response = handler.handle(given_event, given_context)

        assert response == {
            "statusCode": 500,
            "headers": {"content-type": "application/json"},
            "body": '{"request_id": "testRequestId", "documentation_url": "EMPTY DOC", "message": "Boom"}'
        }
