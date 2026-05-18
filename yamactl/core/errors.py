"""Exception hierarchy with stable exit codes for shell scripting."""

from __future__ import annotations


class YamaCtlError(Exception):
    """Base error for all yamactl errors."""


class ConfigError(YamaCtlError):
    """Config missing, malformed, or profile not found. Exit 2."""


class ReceiverUnavailable(YamaCtlError):
    """Cannot connect to receiver. Exit 10."""


class ReceiverBusy(YamaCtlError):
    """Receiver already has an active connection (YNCA limit). Exit 11."""


class CommandTimeout(YamaCtlError):
    """Command did not complete within timeout. Exit 12."""


class InvalidInputSource(YamaCtlError):
    """Requested input source not available. Exit 20."""


class ProtocolUnsupported(YamaCtlError):
    """Operation not supported by the configured protocol adapter. Exit 21."""


class UnexpectedResponse(YamaCtlError):
    """Receiver returned an unparseable or error response. Exit 30."""


EXIT_CODES: dict[type[YamaCtlError], int] = {
    ConfigError: 2,
    ReceiverUnavailable: 10,
    ReceiverBusy: 11,
    CommandTimeout: 12,
    InvalidInputSource: 20,
    ProtocolUnsupported: 21,
    UnexpectedResponse: 30,
}
