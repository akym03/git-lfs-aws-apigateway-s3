import json
import os

from git_lfs_aws_lambda.object_handler import ObjectHandler
from git_lfs_aws_lambda.lock_handler import LockHandler


from git_lfs_aws_lambda.s3_datastore import S3Datastore


def lambda_handler(event, context):
    method_post = {
        '/{repoName}/info/lfs/objects/batch': batch_hander,
        '/{repoName}/info/lfs/objects/batch/verify': verify_object_handler,
        '/{repoName}/info/lfs/locks/verify': verify_lock_handler,
        '/{repoName}/info/lfs/locks': create_lock_handler,
        '/{repoName}/info/lfs/locks/{id}/unlock': delete_lock_handler,
    }
    method_get = {
        '/{repoName}/info/lfs/locks': list_locks_handler,
    }

    try:
        resource = event['resource']
        if (event['httpMethod'] == 'POST'):
            handler = method_post[resource](event, context)
        elif (event['httpMethod'] == 'GET'):
            handler = method_get[resource](event, context)
        else:
            return {
                "statusCode": 405,
                "message": "not found"
            }

        return handler.handle(event, context)
    except KeyError:
        return {
            "statusCode": 404,
            "message": "not found"
        }


def batch_hander(event, context):
    resource = event["resource"]
    datastore = S3Datastore(os.environ["ARTIFACTS_BUCKET"])
    op = json.loads(event["body"])["operation"]

    return ObjectHandler(op, datastore, os.environ["ENDPOINT"], resource)


def verify_object_handler(event, context):
    resource = event["resource"]
    datastore = S3Datastore(os.environ["ARTIFACTS_BUCKET"])
    return ObjectHandler("verify", datastore, os.environ["ENDPOINT"], resource)


def verify_lock_handler(event, context):
    return LockHandler("verify")


def create_lock_handler(event, context):
    return LockHandler("create")


def delete_lock_handler(event, context):
    return LockHandler("delete")


def list_locks_handler(event, context):
    return LockHandler("list")
