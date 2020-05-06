import json
import pytest
import re

import botocore

from git_lfs_aws_lambda.object_handler import ObjectHandler
from git_lfs_aws_lambda.datastore import Datastore
from git_lfs_aws_lambda.lfs_error import LfsError

from ..fake_lambda_context import FakeLambdaContext


class TestObjectHandler:

    INTEGRATION_ENDPOINT = "gllApiIntegrationTestEndpoint"
    MISSING_KEY_1 = "missingKey1"
    MISSING_KEY_2 = "missingKey2"
    EXISTING_KEY_1 = "existingKey1"
    EXISTING_KEY_2 = "existingKey2"
    EXISTING_KEY_SIZE = 64
    TRANSFER_TYPE = "basic"
    VERIFY_URL_REGEX = re.compile(f"^https?://{INTEGRATION_ENDPOINT}/.*/verify$")

    def request_with_body(body):
        return {
            "event": {
                "body": json.dumps(body),
                "requestContext": {
                    "stage": "integrationTest"
                },
                "resource": "/integration/test/resource"
            },
            "context": FakeLambdaContext()
        }

    class TestUploads:

        def __upload_url_for(key):
            return "UPLOAD_" + key

        @pytest.fixture(scope='function', autouse=True)
        def setup(self, mocker):
            def mock_exists(key):
                if (key == TestObjectHandler.EXISTING_KEY_1):
                    return True
                if (key == TestObjectHandler.MISSING_KEY_1):
                    return False
                if (key == TestObjectHandler.MISSING_KEY_2):
                    return False

                raise Exception("Unhandled test exception: exist")

            def mock_get_upload_url(key):
                if (key == TestObjectHandler.EXISTING_KEY_1):
                    raise Exception("Should not be uploading this!")
                if (key == TestObjectHandler.MISSING_KEY_1):
                    return TestObjectHandler.TestUploads.__upload_url_for(key)
                if (key == TestObjectHandler.MISSING_KEY_2):
                    return TestObjectHandler.TestUploads.__upload_url_for(key)

                raise Exception("Unhandled test exception: upload")

            mocker.patch('git_lfs_aws_lambda.datastore.Datastore.exists').side_effect = mock_exists
            mocker.patch('git_lfs_aws_lambda.datastore.Datastore.get_upload_url').side_effect = mock_get_upload_url

            self.handler = ObjectHandler(
                "upload",
                Datastore(),
                TestObjectHandler.INTEGRATION_ENDPOINT,
                "/test/resource/path")

        def test_should_refuse_unkown_transfer_type(self):
            given = TestObjectHandler.request_with_body({"transfers": ["somethingWeird"]})
            response = self.handler.handle(given["event"], given["context"])

            assert response["statusCode"] == 422

            actual = json.loads(response["body"])
            assert actual["message"] == "Unsupported transfer type: ['somethingWeird']"
            assert re.match("^http", actual["documentation_url"]) is not None

        def test_should_process_valid_upload_request(self):
            fake_a = {"oid": TestObjectHandler.MISSING_KEY_1, "size": 10}
            fake_b = {"oid": TestObjectHandler.MISSING_KEY_2, "size": 20}
            given = TestObjectHandler.request_with_body({"objects": [fake_a, fake_b]})

            response = self.handler.handle(given["event"], given["context"])
            assert response["statusCode"] == 200

            actual = json.loads(response["body"])
            assert actual["transfer"] == TestObjectHandler.TRANSFER_TYPE
            assert len(actual["objects"]) == 2

            assert actual["objects"][0]["oid"] == TestObjectHandler.MISSING_KEY_1
            assert actual["objects"][0]["size"] == 10
            assert actual["objects"][0]["actions"]["upload"]["href"] == \
                TestObjectHandler.TestUploads.__upload_url_for(TestObjectHandler.MISSING_KEY_1)
            assert actual["objects"][0]["actions"]["upload"]["expires"] >= 0
            assert TestObjectHandler.VERIFY_URL_REGEX.match(actual["objects"][0]["actions"]["verify"]["href"]) \
                is not None

            assert actual["objects"][1]["oid"] == TestObjectHandler.MISSING_KEY_2
            assert actual["objects"][1]["size"] == 20
            assert actual["objects"][1]["actions"]["upload"]["href"] == \
                TestObjectHandler.TestUploads.__upload_url_for(TestObjectHandler.MISSING_KEY_2)
            assert actual["objects"][1]["actions"]["upload"]["expires"] >= 0
            assert TestObjectHandler.VERIFY_URL_REGEX.match(actual["objects"][1]["actions"]["verify"]["href"]) \
                is not None

        def test_should_skip_uploads_for_existsng_object(self):
            fake_a = {"oid": TestObjectHandler.EXISTING_KEY_1, "size": TestObjectHandler.EXISTING_KEY_SIZE}
            fake_b = {"oid": TestObjectHandler.MISSING_KEY_2, "size": 20}
            given = TestObjectHandler.request_with_body({"objects": [fake_a, fake_b]})

            response = self.handler.handle(given["event"], given["context"])
            assert response["statusCode"] == 200

            actual = json.loads(response["body"])

            assert actual["transfer"] == TestObjectHandler.TRANSFER_TYPE
            assert len(actual["objects"]) == 2

            assert actual["objects"][0]["oid"] == TestObjectHandler.EXISTING_KEY_1
            assert actual["objects"][0]["size"] == TestObjectHandler.EXISTING_KEY_SIZE
            assert "actions" not in actual["objects"][0]

            assert actual["objects"][1]["oid"] == TestObjectHandler.MISSING_KEY_2
            assert actual["objects"][1]["size"] == 20
            assert actual["objects"][1]["actions"]["upload"]["href"] == \
                TestObjectHandler.TestUploads.__upload_url_for(TestObjectHandler.MISSING_KEY_2)
            assert actual["objects"][1]["actions"]["upload"]["expires"] >= 0
            assert TestObjectHandler.VERIFY_URL_REGEX.match(actual["objects"][1]["actions"]["verify"]["href"]) \
                is not None

        def test_should_wrap_individual_object_errors(self):
            fake_a = {"oid": "boom", "size": 1}
            fake_b = {"oid": TestObjectHandler.MISSING_KEY_2, "size": 20}
            given = TestObjectHandler.request_with_body({"objects": [fake_a, fake_b]})

            response = self.handler.handle(given["event"], given["context"])
            assert response["statusCode"] == 200

            actual = json.loads(response["body"])

            assert actual["transfer"] == TestObjectHandler.TRANSFER_TYPE
            assert len(actual["objects"]) == 2

            assert actual["objects"][0]["oid"] == "boom"
            assert actual["objects"][0]["size"] == 1
            assert "actions" not in actual["objects"][0]
            assert actual["objects"][0]["error"]["code"] == 500
            assert actual["objects"][0]["error"]["message"] == "Unhandled test exception: exist"

            assert actual["objects"][1]["oid"] == TestObjectHandler.MISSING_KEY_2
            assert actual["objects"][1]["size"] == 20
            assert actual["objects"][1]["actions"]["upload"]["href"] == \
                TestObjectHandler.TestUploads.__upload_url_for(TestObjectHandler.MISSING_KEY_2)
            assert actual["objects"][1]["actions"]["upload"]["expires"] >= 0
            assert TestObjectHandler.VERIFY_URL_REGEX.match(actual["objects"][1]["actions"]["verify"]["href"]) \
                is not None

    class TestDownloads:

        def __download_url_for(key):
            return "DOWNLOAD_" + key

        @pytest.fixture(scope='function', autouse=True)
        def setup(self, mocker):
            def mock_exists(key):
                if (key == TestObjectHandler.EXISTING_KEY_1):
                    return True
                if (key == TestObjectHandler.EXISTING_KEY_2):
                    return True
                if (key == TestObjectHandler.MISSING_KEY_1):
                    return False
                if (key == TestObjectHandler.MISSING_KEY_2):
                    return False

                raise Exception("Unhandled test exception: exist")

            def mock_get_download_url(key):
                if (key == TestObjectHandler.EXISTING_KEY_1):
                    return TestObjectHandler.TestDownloads.__download_url_for(key)
                if (key == TestObjectHandler.EXISTING_KEY_2):
                    return TestObjectHandler.TestDownloads.__download_url_for(key)
                if (key == TestObjectHandler.MISSING_KEY_1):
                    raise Exception("Should not be uploading this!")
                if (key == TestObjectHandler.MISSING_KEY_2):
                    raise Exception("Should not be uploading this!")

                raise Exception("Unhandled test exception: download")

            mocker.patch('git_lfs_aws_lambda.datastore.Datastore.exists').side_effect = mock_exists
            mocker.patch('git_lfs_aws_lambda.datastore.Datastore.get_download_url').side_effect = mock_get_download_url

            self.handler = ObjectHandler(
                "download",
                Datastore(),
                TestObjectHandler.INTEGRATION_ENDPOINT,
                "/test/resource/path")

        def test_should_process_valid_download_request(self):
            fake_a = {"oid": TestObjectHandler.EXISTING_KEY_1, "size": 10}
            fake_b = {"oid": TestObjectHandler.EXISTING_KEY_2, "size": 20}
            given = TestObjectHandler.request_with_body({"objects": [fake_a, fake_b]})

            response = self.handler.handle(given["event"], given["context"])
            assert response["statusCode"] == 200

            actual = json.loads(response["body"])

            assert actual["transfer"] == TestObjectHandler.TRANSFER_TYPE
            assert len(actual["objects"]) == 2

            assert actual["objects"][0]["oid"] == TestObjectHandler.EXISTING_KEY_1
            assert actual["objects"][0]["size"] == 10
            assert actual["objects"][0]["actions"]["download"]["href"] == \
                TestObjectHandler.TestDownloads.__download_url_for(TestObjectHandler.EXISTING_KEY_1)
            assert actual["objects"][0]["actions"]["download"]["expires"] > 0

            assert actual["objects"][1]["oid"] == TestObjectHandler.EXISTING_KEY_2
            assert actual["objects"][1]["size"] == 20
            assert actual["objects"][1]["actions"]["download"]["href"] == \
                TestObjectHandler.TestDownloads.__download_url_for(TestObjectHandler.EXISTING_KEY_2)
            assert actual["objects"][1]["actions"]["download"]["expires"] > 0

        def test_should_give_404_for_missing_objects(self):
            fake_a = {"oid": TestObjectHandler.MISSING_KEY_1, "size": 10}
            fake_b = {"oid": TestObjectHandler.EXISTING_KEY_1, "size": 20}
            given = TestObjectHandler.request_with_body({"objects": [fake_a, fake_b]})

            response = self.handler.handle(given["event"], given["context"])

            assert response["statusCode"] == 200
            actual = json.loads(response["body"])

            assert actual["transfer"] == TestObjectHandler.TRANSFER_TYPE
            assert len(actual["objects"]) == 2

            assert actual["objects"][0]["oid"] == TestObjectHandler.MISSING_KEY_1
            assert actual["objects"][0]["size"] == 10
            assert "actions" not in actual["objects"][0]
            assert actual["objects"][0]["error"]["code"] == 404
            assert actual["objects"][0]["error"]["message"] == f"Object {TestObjectHandler.MISSING_KEY_1} not exist."

            assert actual["objects"][1]["oid"] == TestObjectHandler.EXISTING_KEY_1
            assert actual["objects"][1]["size"] == 20
            assert actual["objects"][1]["actions"]["download"]["href"] == \
                TestObjectHandler.TestDownloads.__download_url_for(TestObjectHandler.EXISTING_KEY_1)
            assert actual["objects"][1]["actions"]["download"]["expires"] > 0

        def test_should_wrap_other_download_errors(self):
            fake_a = {"oid": "boom", "size": 10}
            fake_b = {"oid": TestObjectHandler.EXISTING_KEY_1, "size": 20}
            given = TestObjectHandler.request_with_body({"objects": [fake_a, fake_b]})

            response = self.handler.handle(given["event"], given["context"])
            assert response["statusCode"] == 200

            actual = json.loads(response["body"])

            assert actual["transfer"] == TestObjectHandler.TRANSFER_TYPE
            assert len(actual["objects"]) == 2

            assert actual["objects"][0]["oid"] == "boom"
            assert actual["objects"][0]["size"] == 10
            assert "actions" not in actual["objects"][0]
            assert actual["objects"][0]["error"]["code"] == 500
            assert actual["objects"][0]["error"]["message"] == "Unhandled test exception: exist"

            assert actual["objects"][1]["oid"] == TestObjectHandler.EXISTING_KEY_1
            assert actual["objects"][1]["size"] == 20
            assert actual["objects"][1]["actions"]["download"]["href"] == \
                TestObjectHandler.TestDownloads.__download_url_for(TestObjectHandler.EXISTING_KEY_1)
            assert actual["objects"][1]["actions"]["download"]["expires"] > 0

    class TestVerify:

        @pytest.fixture(scope='function', autouse=True)
        def setup(self, mocker):
            def mock_exists(key):
                if (key == TestObjectHandler.EXISTING_KEY_1):
                    return True
                if (key == TestObjectHandler.MISSING_KEY_1):
                    return False

                raise Exception("Unhandled test exception: exist")

            def mock_get_info(key):
                if (key == TestObjectHandler.EXISTING_KEY_1):
                    return {"ContentLength": TestObjectHandler.EXISTING_KEY_SIZE}
                if (key == TestObjectHandler.MISSING_KEY_1):
                    raise botocore.exceptions.ClientError({
                        "Error": {
                            "Code": 404,
                            "Message": f"Mock s3: no suck key {key}"
                        }
                    }, "head_object")

                raise Exception("Unhandled test exception: get_info")

            mocker.patch('git_lfs_aws_lambda.datastore.Datastore.exists').side_effect = mock_exists
            mocker.patch('git_lfs_aws_lambda.datastore.Datastore.get_info').side_effect = mock_get_info

            self.handler = ObjectHandler(
                "verify",
                Datastore(),
                TestObjectHandler.INTEGRATION_ENDPOINT,
                "/test/resource/path")

        def test_should_verify_correct_object(self):
            body = {"oid": TestObjectHandler.EXISTING_KEY_1, "size": TestObjectHandler.EXISTING_KEY_SIZE}
            given = TestObjectHandler.request_with_body(body)

            response = self.handler.handle(given["event"], given["context"])
            assert response["statusCode"] == 200

            actual = json.loads(response["body"])

            assert actual == body

        def test_should_verify_incorrect_object(self):
            body = {"oid": TestObjectHandler.EXISTING_KEY_1, "size": 12}
            given = TestObjectHandler.request_with_body(body)

            response = self.handler.handle(given["event"], given["context"])
            assert response["statusCode"] == 411

            actual = json.loads(response["body"])

            assert actual["message"] == f"Expected object of size 12 but found {TestObjectHandler.EXISTING_KEY_SIZE}"

        def test_should_verify_missing_object(self):
            body = {"oid": TestObjectHandler.MISSING_KEY_1, "size": TestObjectHandler.EXISTING_KEY_SIZE}
            given = TestObjectHandler.request_with_body(body)

            response = self.handler.handle(given["event"], given["context"])
            assert response["statusCode"] == 404

            actual = json.loads(response["body"])

            assert actual["message"] == f"Object {TestObjectHandler.MISSING_KEY_1} not found."

        def test_should_wrap_other_errors(self):
            body = {"oid": "boom", "size": TestObjectHandler.EXISTING_KEY_SIZE}
            given = TestObjectHandler.request_with_body(body)

            response = self.handler.handle(given["event"], given["context"])
            assert response["statusCode"] == 500

            actual = json.loads(response["body"])

            assert actual["message"] == f"Unhandled test exception: get_info"

    class TestOperation:

        def test_should_given_unknows_operation(self):

            try:
                ObjectHandler(
                    "boom",
                    Datastore(),
                    TestObjectHandler.INTEGRATION_ENDPOINT,
                    "/test/resource/path")
            except LfsError as actual:
                assert actual.args[0] == 401
                assert actual.args[1] == "Unsupported object operation: [boom]"
