import json


def request_with_body(body):
    return {
        "event": {
            "body": json.dumps(body),
            "requestContext": {
                "stage": "integrationTest"
            },
            "resource": "/integration/test/resource"
        },
        "context": {
            "awsRequestId": "testRequestId"
        }
    }
