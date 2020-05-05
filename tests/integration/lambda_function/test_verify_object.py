import json
import os
import pytest

import botocore

from .create_request import request_with_body
from git_lfs_aws_lambda.lambda_function.verify_object import lambda_handler


class TestVerifyObject:
    MISSING_KEY = "missingKey"
    EXISTING_KEY = "existingKey"
    EXISTING_KEY_SIZE = 128
    INTEGRATION_BUCKET = "gllApiIntegrationTestBucket"

    @staticmethod
    def make_url(operation, bucket, key):
        return f"{operation}:{bucket}/{key}"

    class S3Mock:
        def head_object(self, params):
            if (params['Key'] == TestVerifyObject.EXISTING_KEY):
                return {"ContentLength": TestVerifyObject.EXISTING_KEY_SIZE}

            if (params['Key'] == TestVerifyObject.MISSING_KEY):
                raise botocore.exceptions.ClientError({
                    "Error": {
                        "Code": 404,
                        "Message": f"Mock s3: no suck key {params['Key']}"
                    }
                }, "head_object")

            raise botocore.exceptions.ClientError({
                "Error": {
                    "Code": 500,
                    "Message": f"unkown key {params['Key']}"
                }
            }, "head_object unkown key")

        def get_signed_url(self, operation, params, callback=None):
            if (operation == "put_object" and params['Key'] == TestVerifyObject.MISSING_KEY):
                return callback(None, TestVerifyObject.make_url(operation, params['Bucket'], params['Key']))

            if (operation == "get_object" and params['Key'] == TestVerifyObject.EXISTING_KEY):
                return callback(None, TestVerifyObject.make_url(operation, params['Bucket'], params['Key']))

            return callback("FakeError")

    @pytest.fixture(scope='function', autouse=True)
    def setup(self, mocker):
        os.environ["ARTIFACTS_BUCKET"] = TestVerifyObject.INTEGRATION_BUCKET

        mocker.patch('boto3.client').return_value = TestVerifyObject.S3Mock()
        self.callback = mocker.Mock(return_value=None)

    def test_will_verify_exsisting_objects(self):
        given = request_with_body({
            "oid": TestVerifyObject.EXISTING_KEY,
            "size": TestVerifyObject.EXISTING_KEY_SIZE
        })

        lambda_handler(given["event"], given["context"], self.callback)

        self.callback.assert_called_once()

        assert self.callback.call_args[0][0] is None
        assert self.callback.call_args[0][1]["statusCode"] == 200

    def test_will_not_verify_missing_objects(self):
        given = request_with_body({
            "oid": TestVerifyObject.MISSING_KEY, "size": 1
        })

        lambda_handler(given["event"], given["context"], self.callback)

        self.callback.assert_called_once()
        assert self.callback.call_args[0][0] is None
        assert self.callback.call_args[0][1]["statusCode"] == 404

        actual = json.loads(self.callback.call_args[0][1]["body"])
        assert "message" in actual
        assert "documentation_url" in actual
        assert actual["request_id"] == "testRequestId"

    def test_will_not_verify_with_mismatched_sizeds(self):
        given = request_with_body({
            "oid": TestVerifyObject.EXISTING_KEY,
            "size": 12
        })

        lambda_handler(given["event"], given["context"], self.callback)

        self.callback.assert_called_once()

        assert self.callback.call_args[0][0] is None
        assert self.callback.call_args[0][1]["statusCode"] == 411

        actual = json.loads(self.callback.call_args[0][1]["body"])
        assert "message" in actual
        assert "documentation_url" in actual
        assert actual["request_id"] == "testRequestId"

    def test_will_fail_gracefully(self):
        given = request_with_body({
            "oid": "splode",
            "size": 12
        })

        lambda_handler(given["event"], given["context"], self.callback)

        self.callback.assert_called_once()
        assert self.callback.call_args[0][0] is None
        assert self.callback.call_args[0][1]["statusCode"] == 500

        actual = json.loads(self.callback.call_args[0][1]["body"])
        assert "message" in actual
        assert "documentation_url" in actual
        assert actual["request_id"] == "testRequestId"
