import json
import re

from git_lfs_aws_lambda.lambda_function.list_locks import lambda_handler
from .create_request import request_with_body


class TestListLocks:

    def test_is_not_implemented(self):
        given = request_with_body({})

        response = lambda_handler(given["event"], given["context"])

        assert response["statusCode"] == 501

        actual = json.loads(response["body"])
        assert re.search('not implemented', actual["message"]) is not None
        assert actual["request_id"] == "testRequestId"
        assert actual["documentation_url"] is not None
