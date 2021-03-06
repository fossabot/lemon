from lemon.exception import HttpError
from lemon.response import Response


class Context:
    """The Context object store the current request and response .
    Your can get all information by use ctx in your handler function .
    """

    def __init__(self):
        self.req = None
        self.res = Response()
        # store middleware communication message
        self.state = {}
        self.params = None

    def __setattr__(self, key, value):
        # alias
        if key == 'body':
            self.res.body = value
        if key == 'status':
            self.res.status = value
        else:
            self.__dict__[key] = value

    def __getattr__(self, item):
        # alias
        if item == 'body':
            return self.res.body
        if item == 'status':
            return self.res.status
        return self.__dict__[item]

    def throw(self, status: int, body: str or dict = None):
        """Throw the status and response body"""
        raise HttpError(status=status, body=body)
