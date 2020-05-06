import boto3
from botocore.exceptions import ClientError

from git_lfs_aws_lambda.datastore import Datastore


class S3Datastore(Datastore):
    def __init__(self, bucket_name):
        self.bucket_name = bucket_name
        self.s3 = boto3.client('s3')

    def get_url(self, key, action, content_type=None):
        params = {
            "Bucket": self.bucket_name,
            "Key": key
        }

        if (content_type is not None):
            params['ContentType'] = content_type

        # TODO ClientError をキャッチする例外処理
        return self.s3.generate_presigned_url(action, params)

    def get_upload_url(self, key):
        return self.get_url(key, 'put_object', "application/octet-stream")

    def get_download_url(self, key):
        return self.get_url(key, 'get_object')

    def get_info(self, key):
        return self.s3.head_object(Bucket=self.bucket_name, Key=key)

    def exists(self, key):
        try:
            self.get_info(key)
            return True
        except ClientError:
            return False
