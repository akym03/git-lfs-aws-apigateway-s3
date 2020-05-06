class Action:
    def __init__(self, href, expires=None):
        self.href = href
        self.expires = expires

    def to_dict(self):
        return {"href": self.href, "expires": self.expires}
