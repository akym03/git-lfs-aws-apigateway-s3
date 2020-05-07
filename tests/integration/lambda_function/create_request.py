import json

from ...fake_lambda_context import FakeLambdaContext


def request_with_body(http_method='POST', resource=None, body={}):
    return {
        "event": {
            "httpMethod": http_method,
            "resource": resource,
            "body": json.dumps(body),
            "requestContext": {
                "stage": "integrationTest",
                "domainName": "gllApiIntegrationTestEndpoint"
            },
        },
        "context": FakeLambdaContext
    }
