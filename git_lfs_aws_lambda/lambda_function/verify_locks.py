from git_lfs_aws_lambda.lock_handler import LockHandler


def lambda_handler(event, context, callback):
    handler = LockHandler("verify")
    handler.handle(event, context, callback)
