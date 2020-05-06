import json
import pytest
import re

from git_lfs_aws_lambda.lambda_function.create_locks import lambda_handler
from .create_request import request_with_body


class TestCreateLocks:

    @pytest.fixture(scope="function", autouse=True)
    def setup(self, mocker):
        self.callback = mocker.Mock(return_value=None)

    def test_is_not_implemented(self):
        given = request_with_body({})

        lambda_handler(given["event"], given["context"], self.callback)

        self.callback.assert_called_once()
        assert self.callback.call_args[0][0] is None
        assert self.callback.call_args[0][1]["statusCode"] == 501

        actual = json.loads(self.callback.call_args[0][1]["body"])

        assert re.search('not implemented', actual["message"]) is not None
        assert actual["request_id"] == "testRequestId"
        assert actual["documentation_url"] is not None
