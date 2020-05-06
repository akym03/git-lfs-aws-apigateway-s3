from git_lfs_aws_lambda.lfs_error import LfsError


class Locks:
    def list(self, request=None):
        raise LfsError(501, "Locks: List not implemented")

    def verify(self, request=None):
        return {
            "ours": [],
            "theirs": []
        }

    def create(self, path_to_file=None):
        raise LfsError(500, "Locks: Create not implemented")

    def delete(self, request=None):
        raise LfsError(501, "Locks: Delete not implemented")
