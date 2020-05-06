import pytest

from git_lfs_aws_lambda.lambda_function.handler import lambda_handler
from .create_request import request_with_body


class TestHandler:

    @pytest.mark.parametrize("htmethod, repo_name, expected", [
        ("PUT", "/path/to/repository", 405),
        ("DELETE", "/path/to/repository", 405),
        ("HEAD", "/path/to/repository", 405),
        ("OPTIONS", "/path/to/repository", 405),
        ("GET", "/{repoName}/info/lfs/objects/batch", 404),
        ("POST", "/{repoName}/unknown/path", 404),
        ("GET", "/{repoName}/unknown/path", 404)
    ])
    def test_will_not_defined_method_with_path(self, htmethod, repo_name, expected):
        given = request_with_body(http_method=htmethod, resource=repo_name)

        actual = lambda_handler(given["event"], given["context"])
        assert actual["statusCode"] == expected
