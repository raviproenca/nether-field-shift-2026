# AI-assisted: generated with Claude Code, reviewed by Periélio (pending Ravi)
"""Exceptions raised by the data toolkit. The CLI prints them as one-line messages."""


class DataToolkitError(Exception):
    """Base class for every expected failure."""


class InputError(DataToolkitError, ValueError):
    """Invalid user input (region, dates, variable, output path)."""


class RemoteDataError(DataToolkitError):
    """A NASA service failed, timed out or returned nothing."""


class AuthRequiredError(DataToolkitError):
    """Earthdata Login credentials are missing or rejected."""
