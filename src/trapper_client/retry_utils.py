"""Shared tenacity retry helper for chunked CSV imports.

Network-level failures (read timeouts, connection resets, ...) are the
transient failure this is meant to smooth over — e.g. a server rejecting or
timing out on a chunk that's still too large/slow for it. A 4xx/5xx HTTP
response is a different kind of failure (a validation error, a missing
project, ...); retrying can't fix that, and it never triggers this retry
since the import methods return the raw response instead of raising for it.
"""
from __future__ import annotations

import httpx
from tenacity import Retrying, retry_if_exception_type, stop_after_attempt, wait_exponential


def retrying_for_chunk_upload(attempts: int, min_wait: float, max_wait: float) -> Retrying:
    """Build a tenacity ``Retrying`` instance for one chunk/file upload attempt.

    Retries only on network-level transport errors (timeouts, connection
    resets, DNS failures, ...) — never on HTTP status codes, since those come
    back as plain ``httpx.Response`` objects here, not exceptions.

    Args:
        attempts: Maximum number of attempts (the first try plus retries).
        min_wait: Minimum exponential backoff delay in seconds.
        max_wait: Maximum exponential backoff delay in seconds.

    Returns:
        A ``Retrying`` instance, callable as ``retrying(fn, *args, **kwargs)``.
    """
    return Retrying(
        reraise=True,
        stop=stop_after_attempt(max(1, attempts)),
        wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
        retry=retry_if_exception_type(httpx.TransportError),
    )
