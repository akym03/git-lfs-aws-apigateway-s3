import json
import pytest

from git_lfs_aws_lambda.lambda_function.verify_locks import lambda_handler

from .create_request import request_with_body


class TestVerifyLocks:

    @pytest.fixture(scope='function', autouse=True)
    def setup(self, mocker):
        self.callback = mocker.Mock(return_value=None)

    def test_will_respond_empty(self):
        given = request_with_body({})

        lambda_handler(given["event"], given["context"], self.callback)

        self.callback.assert_called_once()

        assert self.callback.call_args[0][0] is None
        assert self.callback.call_args[0][1]["statusCode"] == 200

        actual = json.loads(self.callback.call_args[0][1]["body"])
        assert len(actual["ours"]) == 0
        assert len(actual["theirs"]) == 0
