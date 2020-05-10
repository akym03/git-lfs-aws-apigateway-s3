import json
import logging
import os

from git_lfs_aws_lambda.object_handler import ObjectHandler
from git_lfs_aws_lambda.lock_handler import LockHandler


from git_lfs_aws_lambda.s3_datastore import S3Datastore


def lambda_handler(event, context):
    logger = logging.getLogger(__name__)

    level_name = os.environ.get('LOG_LEVEL')
    level = logging.getLevelName(level_name)
    if not isinstance(level, int):
        level = logging.INFO
    logger.setLevel(level)

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

    response = {}

    try:
        if ('resource' not in event):
            response = {
                "statusCode": 400,
                "message": "not found resource in event"
            }
        elif ('path' not in event['requestContext']):
            response = {
                "statusCode": 400,
                "message": "not found path in requestContext"
            }
        elif ('domainName' not in event['requestContext']):
            response = {
                "statusCode": 400,
                "message": "not found domainName in requestContext"
            }
        else:
            resource = event['resource']
            if (event['httpMethod'] == 'POST'):
                handler = method_post[resource](event, context)
            elif (event['httpMethod'] == 'GET'):
                handler = method_get[resource](event, context)
            else:
                response = {
                    "statusCode": 405,
                    "message": f"unsupport http method is {event['httpMethod']}"
                }

            response = handler.handle(event, context)
    except KeyError:
        response = {
            "statusCode": 404,
            "message": "resource not found"
        }
    finally:
        logger.info(json.dumps({
            "request": {
                "event": event
            },
            "response": response
        }))

        return response


def batch_hander(event, context):
    request_path = event["requestContext"]["path"]
    endpoint = f'https://{event["requestContext"]["domainName"]}'
    datastore = S3Datastore(os.environ["ARTIFACTS_BUCKET"])
    op = json.loads(event["body"])["operation"]

    return ObjectHandler(op, datastore, endpoint, request_path)


def verify_object_handler(event, context):
    request_path = event["requestContext"]["path"]
    endpoint = f'https://{event["requestContext"]["domainName"]}'
    datastore = S3Datastore(os.environ["ARTIFACTS_BUCKET"])
    return ObjectHandler("verify", datastore, endpoint, request_path)


def verify_lock_handler(event, context):
    return LockHandler("verify")


def create_lock_handler(event, context):
    return LockHandler("create")


def delete_lock_handler(event, context):
    return LockHandler("delete")


def list_locks_handler(event, context):
    return LockHandler("list")
