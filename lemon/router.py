from abc import ABCMeta, abstractmethod
from inspect import signature

import kua

from lemon.config import LEMON_ROUTER_SLASH_SENSITIVE
from lemon.exception import RouterRegisterError, RouterMatchError


class HTTP_METHODS:
    GET = 'GET'
    PUT = 'PUT'
    POST = 'POST'
    DELETE = 'DELETE'


_HTTP_METHODS = [
    HTTP_METHODS.GET,
    HTTP_METHODS.PUT,
    HTTP_METHODS.POST,
    HTTP_METHODS.DELETE,
]


class AbstractRouter(metaclass=ABCMeta):
    @abstractmethod
    def use(self, methods: list, path: str, *middleware_list):
        """Register routes
        :param methods: GET|PUT|POST|DELETE
        :param path: string
        :param middleware_list: async function(ctx, [nxt]) list
        """
        raise NotImplementedError

    @abstractmethod
    def routes(self):
        """Return async function(ctx, [nxt])
        """
        raise NotImplementedError


class AbstractBaseRouter(AbstractRouter, metaclass=ABCMeta):
    def get(self, path: str, *middleware_list):
        """Register GET routes
        :param path: url path
        :param middleware_list: async function(ctx, [nxt]) list
        """
        return self.use([HTTP_METHODS.GET], path, *middleware_list)

    def put(self, path: str, *middleware_list):
        """Register PUT routes
        :param path: url path
        :param middleware_list: async function(ctx, [nxt]) list
        """
        return self.use([HTTP_METHODS.PUT], path, *middleware_list)

    def post(self, path: str, *middleware_list):
        """Register POST routes
        :param path: url path
        :param middleware_list: async function(ctx, [nxt]) list
        """
        return self.use([HTTP_METHODS.POST], path, *middleware_list)

    def delete(self, path: str, *middleware_list):
        """Register DELETE routes
        :param path: url path
        :param middleware_list: async function(ctx, [nxt]) list
        """
        return self.use([HTTP_METHODS.DELETE], path, *middleware_list)

    def all(self, path: str, *middleware_list):
        """Register routes into all http methods
        :param path: url path
        :param middleware_list: async function(ctx, [nxt]) list
        """
        return self.use([
            HTTP_METHODS.GET,
            HTTP_METHODS.PUT,
            HTTP_METHODS.POST,
            HTTP_METHODS.DELETE,
        ], path, *middleware_list)


class SimpleRouter(AbstractBaseRouter):
    def __init__(self, slash=LEMON_ROUTER_SLASH_SENSITIVE):
        self.slash = slash
        self._routes = {
            HTTP_METHODS.GET: {},
            HTTP_METHODS.PUT: {},
            HTTP_METHODS.POST: {},
            HTTP_METHODS.DELETE: {},
        }

    def use(self, methods: list, path: str, *middleware_list):
        """Register routes
        :param methods: GET|PUT|POST|DELETE
        :param path: string
        :param middleware_list: async function(ctx, [nxt]) list
        """
        for method in methods:
            if method not in _HTTP_METHODS:
                raise RouterRegisterError(
                    'Cannot support method : {0}'.format(method)
                )
            if not self.slash and path[-1] == '/':
                path = path[:-1]
            self._routes[method][path] = middleware_list

    def routes(self):
        """Generate async router function(ctx, nxt)
        """

        async def _routes(ctx, nxt):
            method = ctx.req.method
            path = ctx.req.path

            if not self.slash and path[-1] == '/':
                path = path[:-1]

            if path not in self._routes[method]:
                ctx.status = 404
                ctx.body = {
                    'lemon': 'NOT FOUND'
                }
                return

            middleware_list = self._routes[method][path]
            for middleware in middleware_list:
                middleware_params = signature(middleware).parameters
                if len(middleware_params) == 1:
                    await middleware(ctx)
                else:
                    await middleware(ctx, nxt)

        return _routes


class Router(AbstractBaseRouter):
    def __init__(self, slash=LEMON_ROUTER_SLASH_SENSITIVE):
        self.slash = slash
        self._routes = {
            HTTP_METHODS.GET: kua.Routes(),
            HTTP_METHODS.PUT: kua.Routes(),
            HTTP_METHODS.POST: kua.Routes(),
            HTTP_METHODS.DELETE: kua.Routes(),
        }

    def use(self, methods: list, path: str, *middleware_list):
        """Register routes
        :param methods: GET|PUT|POST|DELETE
        :param path: string
        :param middleware_list: async function(ctx, [nxt]) list
        """
        for method in methods:
            if method not in _HTTP_METHODS:
                raise RouterRegisterError(
                    'Cannot support method : {0}'.format(method)
                )
            self._register_middleware_list(method, path, *middleware_list)

    def routes(self):
        """Generate async router function(ctx, nxt)
        """

        async def _routes(ctx, nxt):
            method = ctx.req.method
            path = ctx.req.path
            route = self._match_middleware_list(method=method, path=path)

            if route is None:
                ctx.status = 404
                ctx.body = {
                    'lemon': 'NOT FOUND'
                }
                return

            ctx.params = route.params
            for middleware in route.anything:
                middleware_params = signature(middleware).parameters
                if len(middleware_params) == 1:
                    await middleware(ctx)
                else:
                    await middleware(ctx, nxt)

        return _routes

    def _register_middleware_list(
            self, method: str, path: str, *middleware_list
    ):
        if not self.slash and path[-1] == '/':
            path = path[:-1]

        if method not in _HTTP_METHODS:
            raise RouterMatchError(
                'Method {0} is not supported'.format(method)
            )

        return self._routes[method].add(path, middleware_list)

    def _match_middleware_list(self, method: str, path: str):
        if not self.slash and path[-1] == '/':
            path = path[:-1]

        if method not in _HTTP_METHODS:
            raise RouterMatchError(
                'Method {0} is not supported'.format(method)
            )
        try:
            return self._routes[method].match(path)
        except kua.RouteError:
            return None
