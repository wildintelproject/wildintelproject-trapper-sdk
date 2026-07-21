"""
Exceptions for the Trapper API client.
"""


class APIError(Exception):
    """General API error."""
    pass


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

