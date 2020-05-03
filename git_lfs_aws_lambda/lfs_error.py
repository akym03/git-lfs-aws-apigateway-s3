class LfsError(Exception):
    def __init__(self, code, message):
        self.code = code
        self.message = message

    def get_code(self):
        return self.code
