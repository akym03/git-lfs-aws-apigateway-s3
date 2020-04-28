
from git_lfs_aws_lambda.action import Action


class TestAction:
    def test_should_construct_an_action_object(self):
        given_href = "test href"
        given_expiration = 200

        actual = Action(given_href, given_expiration)

        assert actual.href == given_href
        assert actual.expires == given_expiration

    def test_should_skip_expiration_if_none_provided(self):
        given_href = "test href"

        actual = Action(given_href)

        assert actual.href == given_href
        assert actual.expires is None
