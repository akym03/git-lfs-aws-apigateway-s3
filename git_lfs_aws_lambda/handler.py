import json


class Handler:
    def handle(self, event, context, callback):
        request = json.loads(event['body'])
        try:
            response = self.process(request)
            result = self.lambda_response(response['statusCode'], response['body'])
        except Exception as e:
            code = 500
            body = self.git_lfs_error(e.args[0], self.getDocUrl(code), context['awsRequestId'])
            result = self.lambda_response(code, body)

        callback(None, result)

    def git_lfs_error(self, message, docUrl, requestId):
        return {
            "request_id": requestId,
            "documantation_url": docUrl,
            "message": message,
        }

    def lambda_response(self, statusCode, body):
        return {
            "statusCode": statusCode,
            "headers": {
                "content-type": "application/json"
            },
            "body": json.dumps(body)
        }

    def process(self, request):
        return {}

    def getDocUrl(self, statusCode):
        return "EMPTY DOC"
