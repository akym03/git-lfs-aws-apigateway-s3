from git_lfs_aws_lambda.handler import Handler
from git_lfs_aws_lambda.locks import Locks


class LockHandler(Handler):
    def __init__(self, operation):
        super(Handler, self).__init__

        self.locks = Locks()

        if (operation == "list"):
            self.process = self.locks.list
        elif (operation == "verify"):
            self.process = self.locks.verify
        elif (operation == "create"):
            self.process = self.locks.create
        elif (operation == "delete"):
            self.process = self.locks.delete

    def get_doc_url(self, statusCode):
        return "https://github.com/git-lfs/git-lfs/blob/master/docs/api/locking.md"
