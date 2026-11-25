"""
Exceptions for the Trapper API client.
"""


class APIError(Exception):
    """General API error."""
    pass


class UnsupportedVersionError(APIError):
    """The feature is not available in the Trapper version the server runs."""
    pass


class UnknownFilterWarning(UserWarning):
    """A filter was sent that the server does not apply: Trapper ignores it silently and returns everything.

    The request is still made. Silence it with ``warnings.simplefilter("ignore", err.UnknownFilterWarning)``.
    """


class TransientDownloadError(APIError):
    """A file download was answered with a ``502``, ``503`` or ``504``: worth another attempt."""


class NotFoundError(APIError):
    """HTTP 404 Not Found."""
    pass


class UnauthorizedError(APIError):
    """HTTP 401 Unauthorized."""
    pass


class ForbiddenError(APIError):
    """HTTP 403 Forbidden."""
    pass


class BadRequestError(APIError):
    """HTTP 400 Bad Request."""
    pass


class ServerError(APIError):
    """HTTP 5xx Server Error."""
    pass


class ConflictError(APIError):
    """HTTP 409 Conflict."""
    pass


class UnprocessableEntityError(APIError):
    """HTTP 422 Unprocessable Entity."""
    pass


HTTP_ERRORS_MAP = {
    400: BadRequestError,
    401: UnauthorizedError,
    403: ForbiddenError,
    404: NotFoundError,
    409: ConflictError,
    422: UnprocessableEntityError,
    500: ServerError,
    502: ServerError,
    503: ServerError,
    504: ServerError,
}


def user_stacklevel() -> int:
    """The ``stacklevel`` of a warning that points at the user's code, the first frame outside ``trapper_client``.

    A fixed ``stacklevel`` breaks as soon as a call goes through one more SDK function (a mixin's ``get()``, a
    ``where()`` that calls ``get()``): the warning then names a line of the SDK. Call it right where
    ``warnings.warn`` is called.
    """
    import os
    import sys

    package = os.path.dirname(os.path.abspath(__file__)) + os.sep
    frame = sys._getframe(1)  # the function that warns: stacklevel 1
    level = 1
    while frame is not None and os.path.abspath(frame.f_code.co_filename).startswith(package):
        frame = frame.f_back
        level += 1
    return level
