import os

from git_lfs_aws_lambda.object_handler import ObjectHandler
from git_lfs_aws_lambda.s3_datastore import S3Datastore


def lambda_handler(event, context):
    resource = event["resource"]
    datastore = S3Datastore(os.environ["ARTIFACTS_BUCKET"])
    handler = ObjectHandler("verify", datastore, os.environ["ENDPOINT"], resource)

    return handler.handle(event, context)
