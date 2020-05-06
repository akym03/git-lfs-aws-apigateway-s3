import json

from git_lfs_aws_lambda.lambda_function.verify_locks import lambda_handler

from .create_request import request_with_body


class TestVerifyLocks:

    def test_will_respond_empty(self):
        given = request_with_body({})

        response = lambda_handler(given["event"], given["context"])
        assert response["statusCode"] == 200

        actual = json.loads(response["body"])
        assert len(actual["ours"]) == 0
        assert len(actual["theirs"]) == 0
