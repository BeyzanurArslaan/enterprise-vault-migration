"""Source-side structural contracts for the migration engine.

This module defines the minimal structural interfaces used by the migration
engine to consume Enterprise Vault source data without importing mock source
implementations directly. The contracts remain behavior-free and capture only
the attributes required by the orchestration steps.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Protocol


class SourceRetentionPolicy(Protocol):
    """Structural contract for a source retention policy."""

    @property
    def name(self) -> str:
        """Return the retention policy name."""

    @property
    def retention_days(self) -> int:
        """Return the retention duration in days."""

    @property
    def classification(self) -> str:
        """Return the retention policy classification."""


class SourceAttachment(Protocol):
    """Structural contract for a source attachment."""

    @property
    def filename(self) -> str:
        """Return the attachment filename."""

    @property
    def extension(self) -> str:
        """Return the attachment extension."""

    @property
    def mime_type(self) -> str:
        """Return the attachment MIME type."""

    @property
    def size_bytes(self) -> int:
        """Return the attachment size in bytes."""

    @property
    def checksum(self) -> str:
        """Return the attachment checksum."""


class SourceMailItem(Protocol):
    """Structural contract for a source mail item."""

    @property
    def subject(self) -> str:
        """Return the mail item subject."""

    @property
    def sender(self) -> str:
        """Return the sender address."""

    @property
    def body(self) -> str:
        """Return the message body."""

    @property
    def received_at(self) -> datetime:
        """Return the received timestamp."""

    @property
    def sent_at(self) -> datetime:
        """Return the sent timestamp."""

    @property
    def modified_at(self) -> datetime:
        """Return the modified timestamp."""

    @property
    def internet_message_id(self) -> str:
        """Return the internet message identifier."""

    @property
    def conversation_id(self) -> str:
        """Return the conversation identifier."""

    @property
    def message_size(self) -> int:
        """Return the message size in bytes."""

    @property
    def retention_policy(self) -> SourceRetentionPolicy:
        """Return the retention policy."""

    @property
    def recipients(self) -> Sequence[str]:
        """Return the primary recipients."""

    @property
    def cc_recipients(self) -> Sequence[str]:
        """Return the carbon-copy recipients."""

    @property
    def bcc_recipients(self) -> Sequence[str]:
        """Return the blind-carbon-copy recipients."""

    @property
    def attachments(self) -> Sequence[SourceAttachment]:
        """Return the attachments."""


class SourceMailbox(Protocol):
    """Structural contract for a source mailbox."""

    @property
    def address(self) -> str:
        """Return the mailbox address."""

    @property
    def mail_items(self) -> Sequence[SourceMailItem]:
        """Return the contained mail items."""


class SourceArchive(Protocol):
    """Structural contract for a source archive."""

    @property
    def name(self) -> str:
        """Return the archive name."""

    @property
    def mailboxes(self) -> Sequence[SourceMailbox]:
        """Return the contained mailboxes."""


class SourceVaultStore(Protocol):
    """Structural contract for a source vault store."""

    @property
    def name(self) -> str:
        """Return the vault store name."""

    @property
    def archives(self) -> Sequence[SourceArchive]:
        """Return the contained archives."""


class SourceDatasetGenerator(Protocol):
    """Structural contract for a source dataset generator."""

    def generate_small(self) -> Sequence[SourceVaultStore]:
        """Generate a deterministic source dataset."""


__all__: list[str] = [
    "SourceArchive",
    "SourceAttachment",
    "SourceDatasetGenerator",
    "SourceMailbox",
    "SourceMailItem",
    "SourceRetentionPolicy",
    "SourceVaultStore",
]
