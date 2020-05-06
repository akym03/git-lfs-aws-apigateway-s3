from git_lfs_aws_lambda.lock_handler import LockHandler


def lambda_handler(event, context):
    handler = LockHandler("verify")
    return handler.handle(event, context)
