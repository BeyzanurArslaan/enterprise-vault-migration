"""Exception package for the domain layer.

This package exports the shared domain-level exception hierarchy used by the
application and migration engine to signal structurally invalid workflows.
"""

from __future__ import annotations

from .domain_exceptions import (
    CheckpointError,
    CheckpointNotFoundError,
    DomainException,
    InvalidChecksumError,
    InvalidEmailAddressError,
    InvalidRetentionPeriodError,
    MigrationStateError,
    NonResumableCheckpointError,
    UnsupportedArchiveTypeError,
    UnsupportedCheckpointVersionError,
    ValidationError,
)

__all__: list[str] = [
    "CheckpointError",
    "CheckpointNotFoundError",
    "DomainException",
    "InvalidChecksumError",
    "InvalidEmailAddressError",
    "InvalidRetentionPeriodError",
    "MigrationStateError",
    "NonResumableCheckpointError",
    "UnsupportedArchiveTypeError",
    "UnsupportedCheckpointVersionError",
    "ValidationError",
]
