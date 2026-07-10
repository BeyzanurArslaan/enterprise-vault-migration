"""Generator package for the mock Enterprise Vault subsystem.

This package provides the synthetic dataset generation layer used during
development and testing.
"""

from __future__ import annotations

from mock_ev.loaders import FixtureLoader

from .archive_generator import ArchiveGenerator
from .attachment_generator import AttachmentGenerator
from .dataset_generator import (
    LARGE_PROFILE,
    MEDIUM_PROFILE,
    SMALL_PROFILE,
    DatasetGenerator,
    DatasetProfile,
)
from .mail_generator import MailGenerator
from .mailbox_generator import MailboxGenerator

__all__: list[str] = [
    "ArchiveGenerator",
    "AttachmentGenerator",
    "DatasetGenerator",
    "DatasetProfile",
    "FixtureLoader",
    "LARGE_PROFILE",
    "MailGenerator",
    "MailboxGenerator",
    "MEDIUM_PROFILE",
    "SMALL_PROFILE",
]
