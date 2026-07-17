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

from domain.enums.archive_type import ArchiveType
from domain.enums.item_type import ItemType


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


class SourceContentPart(Protocol):
    """Structural contract for a source SIS content part."""

    @property
    def part_id(self) -> str:
        """Return the content part identifier."""

    @property
    def data_ref(self) -> str:
        """Return the reference used to locate the raw part data."""

    @property
    def data(self) -> bytes:
        """Return the raw content bytes for the part."""

    @property
    def size_bytes(self) -> int:
        """Return the content part size in bytes."""

    @property
    def sha256(self) -> str:
        """Return the content part SHA-256 checksum."""


class SourceShortcut(Protocol):
    """Structural contract for a source shortcut reference."""

    @property
    def target_path(self) -> str:
        """Return the shortcut target path."""

    @property
    def description(self) -> str:
        """Return the shortcut description."""

    @property
    def shortcut_id(self) -> str:
        """Return the shortcut identifier."""

    @property
    def original_source_item_id(self) -> str:
        """Return the original source item identifier."""

    @property
    def archive_id(self) -> str:
        """Return the archive identifier."""

    @property
    def original_path(self) -> str:
        """Return the original source path or folder."""

    @property
    def created_at(self) -> datetime | None:
        """Return the shortcut creation timestamp."""

    @property
    def archived_content_reference(self) -> str | None:
        """Return the archived-content reference."""

    @property
    def status(self) -> str:
        """Return the shortcut status."""


class SourceArchivedFile(Protocol):
    """Structural contract for a source archived file."""

    @property
    def path(self) -> str:
        """Return the archived file path."""

    @property
    def size_bytes(self) -> int:
        """Return the archived file size in bytes."""

    @property
    def checksum(self) -> str | None:
        """Return the archived file checksum."""

    @property
    def file_name(self) -> str | None:
        """Return the archived file name."""

    @property
    def extension(self) -> str | None:
        """Return the archived file extension."""

    @property
    def archived_at(self) -> datetime | None:
        """Return the archived timestamp."""

    @property
    def modified_at(self) -> datetime | None:
        """Return the modified timestamp."""

    @property
    def legal_hold(self) -> bool:
        """Return whether the archived file is under legal hold."""

    @property
    def legal_hold_policy_id(self) -> str | None:
        """Return the legal hold policy identifier."""

    @property
    def source_path(self) -> str | None:
        """Return the original file-system path when one exists."""

    @property
    def shortcut(self) -> SourceShortcut | None:
        """Return the shortcut associated with the archived file."""

    @property
    def item_type(self) -> ItemType:
        """Return the archived file item type."""


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
    def item_type(self) -> ItemType:
        """Return the source item type."""

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

    @property
    def content_parts(self) -> Sequence[SourceContentPart]:
        """Return the SIS content parts for the message body."""

    @property
    def folder_path(self) -> str:
        """Return the source folder path for the mail item."""

    @property
    def legal_hold(self) -> bool:
        """Return whether the item is under legal hold."""

    @property
    def legal_hold_policy_id(self) -> str | None:
        """Return the legal hold policy identifier."""

    @property
    def journal_metadata(self) -> Sequence[tuple[str, str]]:
        """Return journal metadata associated with the source item."""

    @property
    def source_path(self) -> str | None:
        """Return the original source path when one exists."""


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
    def archive_type(self) -> ArchiveType:
        """Return the archive type."""

    @property
    def is_orphaned(self) -> bool:
        """Return whether the archive has no active owner mapping."""

    @property
    def original_owner_identifier(self) -> str | None:
        """Return the original owner identifier when available."""

    @property
    def owner_resolution_status(self) -> str:
        """Return the owner resolution status."""

    @property
    def mailboxes(self) -> Sequence[SourceMailbox]:
        """Return the contained mailboxes."""

    @property
    def journal_archives(self) -> Sequence[SourceJournalArchive]:
        """Return the contained journal archives."""

    @property
    def archived_files(self) -> Sequence[SourceArchivedFile]:
        """Return the contained archived files."""

    @property
    def shortcuts(self) -> Sequence[SourceShortcut]:
        """Return the contained shortcut references."""

    @property
    def source_path(self) -> str | None:
        """Return the original archive path when one exists."""


class SourceJournalArchive(Protocol):
    """Structural contract for a source journal archive."""

    @property
    def name(self) -> str:
        """Return the journal archive name."""

    @property
    def mail_items(self) -> Sequence[SourceMailItem]:
        """Return the contained journal mail items."""


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
    "SourceArchivedFile",
    "SourceAttachment",
    "SourceContentPart",
    "SourceDatasetGenerator",
    "SourceJournalArchive",
    "SourceMailbox",
    "SourceMailItem",
    "SourceRetentionPolicy",
    "SourceShortcut",
    "SourceVaultStore",
]
