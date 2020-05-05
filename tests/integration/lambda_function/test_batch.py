import json
import os
import pytest
import re

from botocore.exceptions import ClientError

from .create_request import request_with_body
from git_lfs_aws_lambda.lambda_function.batch import lambda_handler


class TestBatch:

    MISSING_KEY = "missingKey"
    EXISTING_KEY = "existingKey"
    INTEGRATION_BUCKET = "gllApiIntegrationTestBucket"
    INTEGRATION_ENDPOINT = "gllApiIntegrationTestEndpoint"
    VERIFY_URL_REGEX = re.compile(f"^https?://{INTEGRATION_ENDPOINT}/.*/verify$")

    @staticmethod
    def make_url(operation, bucket, key):
        return f"{operation}:{bucket}/{key}"

    class S3Mock:
        def head_object(self, params):
            if (params['Key'] == TestBatch.EXISTING_KEY):
                return {}

            if (params['Key'] == TestBatch.MISSING_KEY):
                raise ClientError({
                    "Error": {
                        "Code": "NotFound",
                        "message": f"Mock s3: no suck key {params['Key']}"
                    }
                }, "head_object")

            raise ClientError({"Error": {"Code": f"unkown key {params['Key']}"}}, "head_object unkown key")

        def generate_presigned_url(self, operation, params, callback=None):
            if (operation == "put_object" and params['Key'] == TestBatch.MISSING_KEY):
                return TestBatch.make_url(operation, params['Bucket'], params['Key'])

            if (operation == "get_object" and params['Key'] == TestBatch.EXISTING_KEY):
                return TestBatch.make_url(operation, params['Bucket'], params['Key'])

            return "FakeError"

        def get_signed_url(self, operation, params, callback=None):
            if (operation == "put_object" and params['Key'] == TestBatch.MISSING_KEY):
                return callback(None, TestBatch.make_url(operation, params['Bucket'], params['Key']))

            if (operation == "get_object" and params['Key'] == TestBatch.EXISTING_KEY):
                return callback(None, TestBatch.make_url(operation, params['Bucket'], params['Key']))

            return callback("FakeError")

    @pytest.fixture(scope='function', autouse=True)
    def setup(self, mocker):
        os.environ["ARTIFACTS_BUCKET"] = TestBatch.INTEGRATION_BUCKET
        os.environ["ENDPOINT"] = TestBatch.INTEGRATION_ENDPOINT

        mocker.patch('boto3.client').return_value = TestBatch.S3Mock()
        self.callback = mocker.Mock(return_value=None)

    def test_will_provide_upload_url_for_new_objects_and_skip_exists(self):
        given = request_with_body({
            "operation": "upload",
            "objects": [
                {"oid": TestBatch.MISSING_KEY, "size": 25},
                {"oid": TestBatch.EXISTING_KEY, "size": 25}
            ]
        })
        lambda_handler(given["event"], given["context"], self.callback)

        self.callback.assert_called_once()
        assert self.callback.call_args[0][0] is None
        assert self.callback.call_args[0][1]["statusCode"] == 200

        actual = json.loads(self.callback.call_args[0][1]["body"])

        assert len(actual["objects"]) == 2
        assert actual["objects"][0]["actions"]["upload"]["href"] == \
            TestBatch.make_url('put_object', TestBatch.INTEGRATION_BUCKET, TestBatch.MISSING_KEY)
        assert TestBatch.VERIFY_URL_REGEX.match(actual["objects"][0]["actions"]["verify"]["href"]) is not None

        assert "actions" not in actual["objects"][1]

    def test_will_provide_download_url_for_existing_objects_and_error_for_missing(self):
        given = request_with_body({
            "operation": "download",
            "objects": [
                {"oid": TestBatch.MISSING_KEY, "size": 25},
                {"oid": TestBatch.EXISTING_KEY, "size": 25}
            ]
        })

        lambda_handler(given["event"], given["context"], self.callback)

        self.callback.assert_called_once()
        assert self.callback.call_args[0][0] is None
        assert self.callback.call_args[0][1]["statusCode"] == 200

        actual = json.loads(self.callback.call_args[0][1]["body"])

        assert len(actual["objects"]) == 2
        assert "actions" not in actual["objects"][0]
        assert actual["objects"][0]["error"]["code"] == 404
        assert actual["objects"][0]["error"]["message"] is not None
        assert actual["objects"][1]["actions"]["download"]["href"] == \
            TestBatch.make_url("get_object", TestBatch.INTEGRATION_BUCKET, TestBatch.EXISTING_KEY)

    def test_will_wrap_individual_file_errors(self):
        given = request_with_body({
            "operation": "download",
            "objects": [
                {"oid": TestBatch.EXISTING_KEY, "size": 25},
                {"oid": "boom", "size": 25}
            ]
        })

        lambda_handler(given["event"], given["context"], self.callback)

        self.callback.assert_called_once()
        assert self.callback.call_args[0][0] is None
        assert self.callback.call_args[0][1]["statusCode"] == 200

        actual = json.loads(self.callback.call_args[0][1]["body"])

        print(actual["objects"][1])
        assert len(actual["objects"]) == 2
        assert actual["objects"][0]["actions"]["download"]["href"] == \
            TestBatch.make_url("get_object", TestBatch.INTEGRATION_BUCKET, TestBatch.EXISTING_KEY)
        assert actual["objects"][1]["error"]["code"] == 404
        assert actual["objects"][1]["error"]["message"] is not None
