import json


class Handler:
    def handle(self, event, context, callback):
        request = json.loads(event['body'])
        try:
            response = self.process(request)
            result = self.lambda_response(response['statusCode'], response['body'])
        except Exception as e:
            code = 500
            body = self.git_lfs_error(e.args[0], self.get_doc_url(code), context['awsRequestId'])
            result = self.lambda_response(code, body)

        callback(None, result)

    def git_lfs_error(self, message, doc_url, request_id):
        return {
            "request_id": request_id,
            "documantation_url": doc_url,
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
