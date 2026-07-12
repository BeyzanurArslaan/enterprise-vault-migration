"""Domain exception hierarchy for the migration platform.

This module defines the core exception types used to represent invalid domain
state and validation failures in a framework-independent manner.
"""

from __future__ import annotations


class DomainException(Exception):
    """Base exception for all domain-layer errors."""


class ValidationError(DomainException):
    """Raised when a domain value does not satisfy expected constraints."""


class InvalidChecksumError(ValidationError):
    """Raised when a checksum value is invalid."""


class InvalidEmailAddressError(ValidationError):
    """Raised when an email address value is invalid."""


class InvalidRetentionPeriodError(ValidationError):
    """Raised when a retention period value is invalid."""


class MigrationStateError(DomainException):
    """Raised when a migration operation is in an invalid state."""


class UnsupportedArchiveTypeError(DomainException):
    """Raised when an unsupported archive type is encountered."""


class CheckpointError(DomainException):
    """Raised when checkpoint state cannot support the requested workflow."""


class CheckpointNotFoundError(CheckpointError):
    """Raised when a migration checkpoint cannot be located."""


class UnsupportedCheckpointVersionError(CheckpointError):
    """Raised when a checkpoint schema version is not supported."""


class NonResumableCheckpointError(CheckpointError):
    """Raised when a checkpoint cannot safely resume execution."""


__all__: list[str] = [
    "DomainException",
    "ValidationError",
    "InvalidChecksumError",
    "InvalidEmailAddressError",
    "InvalidRetentionPeriodError",
    "MigrationStateError",
    "UnsupportedArchiveTypeError",
    "CheckpointError",
    "CheckpointNotFoundError",
    "UnsupportedCheckpointVersionError",
    "NonResumableCheckpointError",
]
