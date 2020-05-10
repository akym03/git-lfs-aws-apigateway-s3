import json

from ...fake_lambda_context import FakeLambdaContext


def request_with_body(http_method='POST', api_resource=None, request_path=None, body={}):
    return {
        "event": {
            "httpMethod": http_method,
            "resource": api_resource,
            "body": json.dumps(body),
            "requestContext": {
                "path": request_path,
                "stage": "integrationTest",
                "domainName": "gllApiIntegrationTestEndpoint"
            },
        },
        "context": FakeLambdaContext
    }
