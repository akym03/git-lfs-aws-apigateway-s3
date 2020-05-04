import json
import pytest
import re

from git_lfs_aws_lambda.object_handler import ObjectHandler
from git_lfs_aws_lambda.datastore import Datastore


class TestObjectHandler:

    INTEGRATION_ENDPOINT = "gllApiIntegrationTestEndpoint"
    MISSING_KEY_1 = "missingKey1"
    MISSING_KEY_2 = "missingKey2"
    EXISTING_KEY_1 = "existingKey1"
    EXISTING_KEY_2 = "existingKey2"
    EXISTING_KEY_SIZE = 64
    TRANSFER_TYPE = "basic"
    VERIFY_URL_REGEX = re.compile(f"^https?://{INTEGRATION_ENDPOINT}/.*/verify$")

    def request_with_body(body, mocker):

        callback = mocker.Mock(return_value=None)
        return {
            "event": {
                "body": json.dumps(body),
                "requestContext": {
                    "stage": "integrationTest"
                },
                "resource": "/integration/test/resource"
            },
            "context": {
                "awsRequestId": "testRequestId"
            },
            "callback": callback
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

        def test_should_refuse_unkown_transfer_type(self, mocker):
            given = TestObjectHandler.request_with_body({"transfers": ["somethingWeird"]}, mocker)
            self.handler.handle(given["event"], given["context"], given["callback"])

            given["callback"].assert_called_once()
            response = given["callback"].call_args.args[1]

            assert response["statusCode"] == 422

            actual = json.loads(response["body"])
            assert actual["message"] == "Unsupported transfer type: ['somethingWeird']"
            assert re.match("^http", actual["documentation_url"]) is not None

        def test_should_process_valid_upload_request(self, mocker):
            fake_a = {"oid": TestObjectHandler.MISSING_KEY_1, "size": 10}
            fake_b = {"oid": TestObjectHandler.MISSING_KEY_2, "size": 20}
            given = TestObjectHandler.request_with_body({"objects": [fake_a, fake_b]}, mocker)

            self.handler.handle(given["event"], given["context"], given["callback"])

            given["callback"].assert_called_once()
            response = given["callback"].call_args.args[1]

            assert response["statusCode"] == 200

            actual = json.loads(response["body"])
            assert actual["transfer"] == TestObjectHandler.TRANSFER_TYPE
            assert len(actual["objects"]) == 2

            print(actual["objects"][0])
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

        def test_should_skip_uploads_for_existsng_object(self, mocker):
            fake_a = {"oid": TestObjectHandler.EXISTING_KEY_1, "size": TestObjectHandler.EXISTING_KEY_SIZE}
            fake_b = {"oid": TestObjectHandler.MISSING_KEY_2, "size": 20}
            given = TestObjectHandler.request_with_body({"objects": [fake_a, fake_b]}, mocker)

            self.handler.handle(given["event"], given["context"], given["callback"])

            given["callback"].assert_called_once()
            response = given["callback"].call_args.args[1]
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

        def test_should_wrap_individual_object_errors(self, mocker):
            fake_a = {"oid": "boom", "size": 1}
            fake_b = {"oid": TestObjectHandler.MISSING_KEY_2, "size": 20}
            given = TestObjectHandler.request_with_body({"objects": [fake_a, fake_b]}, mocker)

            self.handler.handle(given["event"], given["context"], given["callback"])

            given["callback"].assert_called_once()
            response = given["callback"].call_args.args[1]
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
        def test_should_process_valid_download_request(self):
            pass
