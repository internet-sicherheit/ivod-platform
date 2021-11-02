from django.conf import settings
from json import loads, dumps

from django.core.exceptions import SuspiciousOperation

class TokenCopierMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        # One-time configuration and initialization.

    def __call__(self, request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.
        try:
            JWT_AUTH = getattr(settings, "JWT_AUTH", {})
            JWT_AUTH_COOKIE = JWT_AUTH.get("JWT_AUTH_COOKIE", None)
            if request.path.endswith('/token/refresh/') or request.path.endswith('token/verify/'):
                if JWT_AUTH_COOKIE in request.COOKIES:
                    if request.encoding is None:
                        request.encoding = 'utf-8'
                    if request.content_type == 'application/json':
                        body = loads(request.body.decode(request.encoding))
                        # Set cookie, but only if token isnt set manually already
                        if 'token' not in body:
                            body['token'] = request.COOKIES[JWT_AUTH_COOKIE]
                        request._body = dumps(body).encode(request.encoding)
                    else:
                        raise ValueError("Unsupported content Type")

            response = self.get_response(request)
            if request.path.endswith('/token/blacklist/') and response.status_code == 201:
                response.delete_cookie(JWT_AUTH_COOKIE)
        except Exception as e:
            raise SuspiciousOperation()
        # Code to be executed for each request/response after
        # the view is called.

        return response