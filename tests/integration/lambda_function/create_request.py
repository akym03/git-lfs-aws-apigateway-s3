import json

from ...fake_lambda_context import FakeLambdaContext


def request_with_body(body):
    return {
        "event": {
            "body": json.dumps(body),
            "requestContext": {
                "stage": "integrationTest"
            },
            "resource": "/integration/test/resource"
        },
        "context": FakeLambdaContext
    }
