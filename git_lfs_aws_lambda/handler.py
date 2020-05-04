import json
from logging import getLogger

from git_lfs_aws_lambda.lfs_error import LfsError


class Handler:
    logger = getLogger(__name__)

    def handle(self, event, context, callback):
        request = json.loads(event['body'])
        try:
            response = self.process(request)
            result = self.lambda_response(200, response)
        except LfsError as ex:
            ex_code, ex_message = ex.args
            body = self.git_lfs_error(ex_message, self.get_doc_url(ex_code), context['awsRequestId'])
            result = self.lambda_response(ex_code, body)
        except Exception as ex:
            Handler.logger.exception(ex)
            ex_message = ex.args[0]
            code = 500
            body = self.git_lfs_error(ex_message, self.get_doc_url(code), context['awsRequestId'])
            result = self.lambda_response(code, body)

        callback(None, result)

    def git_lfs_error(self, message, doc_url, request_id):
        return {
            "request_id": request_id,
            "documentation_url": doc_url,
            "message": message,
        }

    def lambda_response(self, status_code, body):
        return {
            "statusCode": status_code,
            "headers": {
                "content-type": "application/json"
            },
            "body": json.dumps(body)
        }

    def process(self, request):
        return {}

    def get_doc_url(self, status_code):
        return "EMPTY DOC"
