import re
import pytest

from git_lfs_aws_lambda.lock_handler import LockHandler
from git_lfs_aws_lambda.lfs_error import LfsError


class TestLockHandler():
    def test_should_raise_on_list(self):
        with pytest.raises(LfsError) as ex:
            handler = LockHandler('list')
            handler.process({"test": "data"})
        assert "(501, 'Locks: List not implemented'" in str(ex.value)

    def test_should_process_verify(self):

        handler = LockHandler('verify')
        actual = handler.process({"test": "data"})

        assert actual == {"ours": [], "theirs": []}

    def test_should_raise_on_create(self):
        with pytest.raises(LfsError) as ex:
            handler = LockHandler('create')
            handler.process({"test": "data"})
        assert "(501, 'Locks: Create not implemented'" in str(ex.value)

    def test_should_raise_on_delete(self):
        with pytest.raises(LfsError) as ex:
            handler = LockHandler('delete')
            handler.process({"test": "data"})
        assert "(501, 'Locks: Delete not implemented'" in str(ex.value)

    def test_shoud_provide_err_doc(self):
        handler = LockHandler('verify')
        doc_url = handler.get_doc_url(500)
        assert re.match('^https', doc_url) is not None
