import json
import os
import pytest
import re

import botocore

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
        def head_object(self, Bucket, Key):
            if (Key == TestBatch.EXISTING_KEY):
                return {}

            if (Key == TestBatch.MISSING_KEY):
                raise botocore.exceptions.ClientError({
                    "Error": {
                        "Code": 404,
                        "Message": f"Mock s3: no suck key {Key}"
                    }
                }, "head_object")

            raise botocore.exceptions.ClientError({
                "Error": {
                    "Code": 500,
                    "Message": f"unkown key {Key}"
                }
            }, "head_object unkown key")

        def generate_presigned_url(self, operation, params):
            if (operation == "put_object" and params['Key'] == TestBatch.MISSING_KEY):
                return TestBatch.make_url(operation, params['Bucket'], params['Key'])

            if (operation == "get_object" and params['Key'] == TestBatch.EXISTING_KEY):
                return TestBatch.make_url(operation, params['Bucket'], params['Key'])

            return "FakeError"

    @pytest.fixture(scope='function', autouse=True)
    def setup(self, mocker):
        os.environ["ARTIFACTS_BUCKET"] = TestBatch.INTEGRATION_BUCKET
        os.environ["ENDPOINT"] = TestBatch.INTEGRATION_ENDPOINT

        mocker.patch('boto3.client').return_value = TestBatch.S3Mock()

    def test_will_provide_upload_url_for_new_objects_and_skip_exists(self):
        given = request_with_body({
            "operation": "upload",
            "objects": [
                {"oid": TestBatch.MISSING_KEY, "size": 25},
                {"oid": TestBatch.EXISTING_KEY, "size": 25}
            ]
        })
        response = lambda_handler(given["event"], given["context"])
        assert response["statusCode"] == 200

        actual = json.loads(response["body"])

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

        response = lambda_handler(given["event"], given["context"])
        assert response["statusCode"] == 200

        actual = json.loads(response["body"])

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

        response = lambda_handler(given["event"], given["context"])
        assert response["statusCode"] == 200

        actual = json.loads(response["body"])

        assert len(actual["objects"]) == 2
        assert actual["objects"][0]["actions"]["download"]["href"] == \
            TestBatch.make_url("get_object", TestBatch.INTEGRATION_BUCKET, TestBatch.EXISTING_KEY)
        assert actual["objects"][1]["error"]["code"] == 404
        assert actual["objects"][1]["error"]["message"] is not None
