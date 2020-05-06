from git_lfs_aws_lambda.lock_handler import LockHandler


def lambda_handler(event, context, callback):
    pass
    handler = LockHandler("create")
    handler.handle(event, context, callback)
