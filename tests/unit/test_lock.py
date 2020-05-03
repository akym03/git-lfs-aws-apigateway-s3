import datetime

from git_lfs_aws_lambda.lock import Lock


class TestLock(object):
    def test_should_construct_a_lock_object(self):
        given_id = "tome-time-uuid"
        given_path = "/path/to/file"
        given_time = datetime.datetime.now().isoformat()
        given_owner = {"name": "Ken Grege"}

        actual = Lock(given_id, given_path, given_time, given_owner)

        assert actual.id == given_id
        assert actual.path == given_path
        assert actual.locked_at == given_time
        assert actual.owner == given_owner
