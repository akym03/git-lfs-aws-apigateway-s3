import pytest

from botocore.exceptions import ClientError

from git_lfs_aws_lambda.s3_datastore import S3Datastore

TEST_BUCKET_NAME = "TEST_BUCKET_NAME"
MESSING_KEY = "missingKey"
EXISTING_KEY = "existingKey"


def makeUrl(operation, bucket, key):
    return f"{operation}:{bucket}/{key}"


class TestS3Datastore:

    class S3Mock:
        def generate_presigned_url(self, operation, params, callback=None):
            print(params)
            if (operation == "put_object" and params['Key'] == MESSING_KEY):
                return makeUrl(operation, params['Bucket'], params['Key'])

            if (operation == "get_object" and params['Key'] == EXISTING_KEY):
                return makeUrl(operation, params['Bucket'], params['Key'])

            return "FakeError"

        def head_object(self, params):
            if (params['Key'] == EXISTING_KEY):
                return {
                    "ContentLength": 64
                }

            if (params['Key'] == MESSING_KEY):
                error_response = {
                    "Error": {
                        "Code": "NotFound"
                    }
                }
                raise ClientError(error_response, "head_object")

            return "FakeError"

    @pytest.fixture(scope='function', autouse=True)
    def scope_function(self, mocker):
        mocker.patch('boto3.client').return_value = TestS3Datastore.S3Mock()
        self.datastore = S3Datastore(TEST_BUCKET_NAME)

    def buildS3Mock(self):
        return None

    def test_should_produce_a_signed_upload_url(self):
        given = MESSING_KEY
        actual = self.datastore.get_upload_url(given)

        assert actual == makeUrl("put_object", TEST_BUCKET_NAME, given)

    def test_should_produce_a_signed_download_url(self):
        given = EXISTING_KEY
        actual = self.datastore.get_download_url(given)

        assert actual == makeUrl("get_object", TEST_BUCKET_NAME, given)

    def test_should_return_if_exists(self):
        given = EXISTING_KEY
        actual = self.datastore.exists(given)

        assert actual is True

    def test_should_return_if_dose_not_exist(self):
        given = MESSING_KEY
        actual = self.datastore.exists(given)

        assert actual is False

    def test_should_return_info_for_existing_object(self):
        given = EXISTING_KEY
        actual = self.datastore.get_info(given)

        assert actual['ContentLength'] == 64
