# AI-assisted: generated with Claude Code, reviewed by Periélio (pending Ravi)
"""Exceptions raised by the data toolkit. The CLI prints them as one-line messages."""

import re
from collections.abc import Iterator
from contextlib import contextmanager


class DataToolkitError(Exception):
    """Base class for every expected failure."""


class InputError(DataToolkitError, ValueError):
    """Invalid user input (region, dates, variable, output path)."""


class RemoteDataError(DataToolkitError):
    """A NASA service failed, timed out or returned nothing."""


class AuthRequiredError(DataToolkitError):
    """Earthdata Login credentials are missing or rejected."""


MAX_DETAIL = 120


def describe_failure(exc: BaseException) -> str:
    """Short, safe text for an unexpected remote failure: HTTP status or class and a trimmed message.

    Never uses repr() of the exception (auth objects) and cuts URL query strings (signed tokens).
    """
    status = getattr(exc, "status", None) or getattr(getattr(exc, "response", None), "status_code", None)
    if status in (401, 403):
        return f"access denied (HTTP {status}); check your login or try again later"
    if status:
        return f"HTTP {status}"
    detail = re.sub(r"\?\S*", "?...", str(exc)).strip()[:MAX_DETAIL]
    return f"{type(exc).__name__}: {detail}" if detail else type(exc).__name__


@contextmanager
def remote_errors(action: str) -> Iterator[None]:
    """Turn any unexpected failure while talking to a remote service or reading its files into RemoteDataError."""
    try:
        yield
    except DataToolkitError:
        raise
    except Exception as exc:  # noqa: BLE001  any remote failure becomes RemoteDataError
        raise RemoteDataError(f"{action} failed: {describe_failure(exc)}") from None


class SizeLimitError(DataToolkitError):
    """The generated snapshot files are larger than the allowed total."""
