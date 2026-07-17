"""Dataset generator for the mock Enterprise Vault subsystem.

This module provides the public entry point for generating complete synthetic
Enterprise Vault vault store hierarchies.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Final, cast

from domain.enums.archive_type import ArchiveType
from domain.enums.item_type import ItemType
from mock_ev.builders import EnterpriseVaultBuilder
from mock_ev.entities import (
    Archive,
    ArchivedFile,
    Attachment,
    ContentPart,
    JournalArchive,
    Mailbox,
    MailItem,
    RetentionPolicy,
    Shortcut,
    VaultStore,
)
from mock_ev.loaders import FixtureLoader

from ._shared import build_generation_context, distribute
from .archive_generator import ArchiveGenerator


@dataclass(frozen=True, slots=True)
class DatasetProfile:
    """Profile describing the target size of a generated dataset."""

    vault_stores: int
    archives: int
    mailboxes: int
    mail_items: int
    attachments: int

    def __getitem__(self, key: str) -> int:
        """Provide dict-style access for compatibility with older tests."""

        return cast(int, getattr(self, key))


SMALL_PROFILE: Final[DatasetProfile] = DatasetProfile(
    vault_stores=2,
    archives=5,
    mailboxes=20,
    mail_items=500,
    attachments=1_200,
)
MEDIUM_PROFILE: Final[DatasetProfile] = DatasetProfile(
    vault_stores=5,
    archives=50,
    mailboxes=200,
    mail_items=10_000,
    attachments=25_000,
)
LARGE_PROFILE: Final[DatasetProfile] = DatasetProfile(
    vault_stores=10,
    archives=500,
    mailboxes=2_000,
    mail_items=100_000,
    attachments=250_000,
)


class DatasetGenerator:
    """Public entry point for generating complete synthetic datasets."""

    def __init__(
        self,
        seed: int | None = None,
        loader: FixtureLoader | None = None,
        archive_generator: ArchiveGenerator | None = None,
        vault_store_builder: EnterpriseVaultBuilder | None = None,
    ) -> None:
        """Create a dataset generator with optional dependency overrides."""

        self._loader = loader or FixtureLoader()
        self._context = build_generation_context(seed, self._loader)
        self._archive_generator = archive_generator or ArchiveGenerator(self._context)
        self._vault_store_builder = vault_store_builder or EnterpriseVaultBuilder()

    def generate_small(self) -> list[VaultStore]:
        """Generate the small predefined dataset profile."""

        return self._generate_dataset(SMALL_PROFILE)

    def generate_medium(self) -> list[VaultStore]:
        """Generate the medium predefined dataset profile."""

        return self._generate_dataset(MEDIUM_PROFILE)

    def generate_large(self) -> list[VaultStore]:
        """Generate the large predefined dataset profile."""

        return self._generate_dataset(LARGE_PROFILE)

    def generate_mixed(self) -> list[VaultStore]:
        """Generate the deterministic mixed Enterprise Vault dataset."""

        started_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
        shared_part = self._build_content_part(
            part_id="sis-shared-part",
            data=b"Shared SIS body content",
        )
        unique_part = self._build_content_part(
            part_id="sis-unique-part",
            data=b"Unique SIS body content",
        )
        alternate_shared_part = self._build_content_part(
            part_id="sis-shared-part-alt",
            data=b"Shared journal body content",
        )

        mailbox_archive = Archive(
            name="Mailbox Archive",
            archive_type=ArchiveType.MAILBOX,
            mailboxes=[
                Mailbox(
                    address="alice@example.com",
                    mail_items=[
                        self._build_mail_item(
                            subject="Inbox Update",
                            sender="alice@example.com",
                            body="Inbox update body",
                            internet_message_id="mailbox-item-1",
                            conversation_id="conversation-mailbox-1",
                            folder_path="/Inbox",
                            received_at=started_at,
                            sent_at=started_at - timedelta(hours=1),
                            modified_at=started_at + timedelta(minutes=5),
                            retention_policy=self._build_retention_policy("Standard"),
                            attachments=(
                                self._build_attachment(
                                    filename="inbox-note.txt",
                                    size_bytes=128,
                                ),
                            ),
                            content_parts=(shared_part,),
                        ),
                        self._build_mail_item(
                            subject="Project Alpha",
                            sender="alice@example.com",
                            body="Project alpha body",
                            internet_message_id="mailbox-item-2",
                            conversation_id="conversation-mailbox-2",
                            folder_path="/Projects/Alpha",
                            received_at=started_at + timedelta(minutes=10),
                            sent_at=started_at,
                            modified_at=started_at + timedelta(minutes=15),
                            retention_policy=self._build_retention_policy("Legal Hold"),
                            attachments=(),
                            content_parts=(shared_part, unique_part),
                            legal_hold=True,
                            legal_hold_policy_id="LHP-ALPHA",
                        ),
                        self._build_mail_item(
                            subject="Sent Notice",
                            sender="alice@example.com",
                            body="Sent notice body",
                            internet_message_id="mailbox-item-3",
                            conversation_id="conversation-mailbox-3",
                            folder_path="/Sent Items",
                            received_at=started_at + timedelta(minutes=20),
                            sent_at=started_at + timedelta(minutes=18),
                            modified_at=started_at + timedelta(minutes=25),
                            retention_policy=self._build_retention_policy("Standard"),
                            attachments=(),
                            content_parts=(),
                        ),
                    ],
                ),
            ],
            shortcuts=[
                self._build_shortcut(
                    shortcut_id="shortcut-valid-1",
                    original_source_item_id="mailbox-item-1",
                    archive_id="Mailbox Archive",
                    original_path="/Inbox/Inbox Update",
                    created_at=started_at,
                    archived_content_reference="mailbox-item-1",
                    status="valid",
                ),
            ],
        )
        journal_archive = Archive(
            name="Journal Archive",
            archive_type=ArchiveType.JOURNAL,
            owner_resolution_status="not_applicable",
            journal_archives=[
                JournalArchive(
                    name="Journal 2026",
                    retention_days=3_650,
                    mail_items=[
                        self._build_mail_item(
                            subject="Journal Entry",
                            sender="journal@example.com",
                            body="Journal body",
                            internet_message_id="journal-item-1",
                            conversation_id="conversation-journal-1",
                            folder_path="/Journal/2026",
                            received_at=started_at + timedelta(minutes=30),
                            sent_at=started_at + timedelta(minutes=29),
                            modified_at=started_at + timedelta(minutes=35),
                            retention_policy=self._build_retention_policy("Journal"),
                            attachments=(),
                            content_parts=(alternate_shared_part,),
                            item_type=ItemType.JOURNAL,
                            legal_hold=True,
                            legal_hold_policy_id="LHP-JOURNAL",
                            journal_metadata=(
                                ("journal_id", "journal-2026"),
                                ("envelope_id", "envelope-1"),
                            ),
                        ),
                    ],
                ),
            ],
        )
        orphaned_archive = Archive(
            name="Orphaned Archive",
            archive_type=ArchiveType.MAILBOX,
            is_orphaned=True,
            original_owner_identifier="orphaned.owner@example.com",
            owner_resolution_status="orphaned",
            mailboxes=[
                Mailbox(
                    address="orphaned.owner@example.com",
                    mail_items=[
                        self._build_mail_item(
                            subject="Orphaned Record",
                            sender="orphaned.owner@example.com",
                            body="Orphaned body",
                            internet_message_id="orphaned-item-1",
                            conversation_id="conversation-orphaned-1",
                            folder_path="/Archive/Orphans",
                            received_at=started_at + timedelta(minutes=40),
                            sent_at=started_at + timedelta(minutes=39),
                            modified_at=started_at + timedelta(minutes=45),
                            retention_policy=self._build_retention_policy("Orphaned"),
                            attachments=(),
                            content_parts=(shared_part,),
                            legal_hold=False,
                        ),
                    ],
                ),
            ],
        )
        fsa_archive = Archive(
            name="FSA Archive",
            archive_type=ArchiveType.FSA,
            owner_resolution_status="unsupported",
            source_path="/files/projects",
            archived_files=[
                self._build_archived_file(
                    path="/files/projects/contracts/contract-1.docx",
                    size_bytes=2_048,
                    checksum="fsa-contract-1",
                    file_name="contract-1.docx",
                    extension="docx",
                    archived_at=started_at + timedelta(minutes=50),
                    modified_at=started_at + timedelta(minutes=49),
                    retention_policy=self._build_retention_policy("File System"),
                    legal_hold=False,
                    legal_hold_policy_id=None,
                    source_path="/files/projects/contracts/contract-1.docx",
                    shortcut=self._build_shortcut(
                        shortcut_id="shortcut-broken-1",
                        original_source_item_id="fsa-file-1",
                        archive_id="FSA Archive",
                        original_path="/files/projects/contracts/contract-1.docx",
                        created_at=started_at + timedelta(minutes=48),
                        archived_content_reference="fsa-file-1",
                        status="broken",
                    ),
                ),
            ],
            shortcuts=[
                self._build_shortcut(
                    shortcut_id="shortcut-stale-2",
                    original_source_item_id="fsa-file-1",
                    archive_id="FSA Archive",
                    original_path="/files/projects/contracts/contract-1.docx",
                    created_at=started_at + timedelta(minutes=48),
                    archived_content_reference="fsa-file-1",
                    status="stale",
                ),
            ],
        )

        vault_store_a = self._vault_store_builder.build_vault_store(
            name="Vault Store A",
            archives=(mailbox_archive, journal_archive),
        )
        vault_store_b = self._vault_store_builder.build_vault_store(
            name="Vault Store B",
            archives=(orphaned_archive, fsa_archive),
        )
        return [vault_store_a, vault_store_b]

    def _generate_dataset(self, profile: DatasetProfile) -> list[VaultStore]:
        """Generate a complete vault store hierarchy for a profile."""

        archive_counts = distribute(profile.archives, profile.vault_stores, self._context.rng)
        mailbox_counts = distribute(profile.mailboxes, profile.archives, self._context.rng)
        mail_item_counts = distribute(profile.mail_items, profile.mailboxes, self._context.rng)
        attachment_counts = distribute(profile.attachments, profile.mail_items, self._context.rng)

        mailbox_counts_iter = iter(mailbox_counts)
        mail_item_counts_iter = iter(mail_item_counts)
        attachment_counts_iter = iter(attachment_counts)
        vault_stores: list[VaultStore] = []

        for vault_store_index, archive_count in enumerate(archive_counts, start=1):
            archives: list[Archive] = []
            for _ in range(archive_count):
                mailbox_attachment_counts: list[list[int]] = []
                mailbox_count = next(mailbox_counts_iter)
                for _ in range(mailbox_count):
                    mail_item_count = next(mail_item_counts_iter)
                    mailbox_attachment_counts.append(
                        [next(attachment_counts_iter) for _ in range(mail_item_count)]
                    )
                archives.append(
                    self._archive_generator.generate_one(
                        mailbox_attachment_counts=tuple(mailbox_attachment_counts),
                    )
                )
            vault_stores.append(
                self._vault_store_builder.build_vault_store(
                    name=self._vault_store_name(vault_store_index),
                    archives=archives,
                )
            )

        return vault_stores

    def _vault_store_name(self, index: int) -> str:
        """Create a deterministic vault store name."""

        return f"{self._context.faker.company()} Vault Store {index}"

    def _build_mail_item(
        self,
        *,
        subject: str,
        sender: str,
        body: str,
        internet_message_id: str,
        conversation_id: str,
        folder_path: str,
        received_at: datetime,
        sent_at: datetime,
        modified_at: datetime,
        retention_policy: RetentionPolicy,
        attachments: tuple[Attachment, ...],
        content_parts: tuple[ContentPart, ...],
        item_type: ItemType = ItemType.EMAIL,
        legal_hold: bool = False,
        legal_hold_policy_id: str | None = None,
        journal_metadata: tuple[tuple[str, str], ...] = (),
    ) -> MailItem:
        """Build a deterministic mock mail item for mixed datasets."""

        message_size = len(body.encode("utf-8")) + sum(
            attachment.size_bytes for attachment in attachments
        )
        return MailItem(
            subject=subject,
            sender=sender,
            body=body,
            received_at=received_at,
            sent_at=sent_at,
            modified_at=modified_at,
            internet_message_id=internet_message_id,
            conversation_id=conversation_id,
            message_size=message_size,
            retention_policy=retention_policy,
            item_type=item_type,
            recipients=["recipient@example.com"],
            cc_recipients=[],
            bcc_recipients=[],
            attachments=list(attachments),
            content_parts=list(content_parts),
            folder_path=folder_path,
            legal_hold=legal_hold,
            legal_hold_policy_id=legal_hold_policy_id,
            journal_metadata=journal_metadata,
        )

    def _build_attachment(
        self,
        *,
        filename: str,
        size_bytes: int,
    ) -> Attachment:
        """Build a deterministic attachment for mixed datasets."""

        extension = filename.rsplit(".", maxsplit=1)[-1] if "." in filename else ""
        checksum = hashlib.sha256(
            f"{filename}|{extension}|{size_bytes}".encode(),
        ).hexdigest()
        return Attachment(
            filename=filename,
            extension=extension,
            mime_type="application/octet-stream",
            size_bytes=size_bytes,
            checksum=checksum,
        )

    def _build_content_part(self, *, part_id: str, data: bytes) -> ContentPart:
        """Build a deterministic SIS content part for mixed datasets."""

        return ContentPart(
            part_id=part_id,
            data_ref=f"sis://{part_id}",
            data=data,
            size_bytes=len(data),
            sha256=hashlib.sha256(data).hexdigest(),
        )

    def _build_retention_policy(self, name: str) -> RetentionPolicy:
        """Build a deterministic retention policy for mixed datasets."""

        retention_days = {
            "Standard": 365,
            "Legal Hold": 1_825,
            "Journal": 1_095,
            "Orphaned": 730,
            "File System": 540,
        }.get(name, 365)
        classification = {
            "Standard": "general",
            "Legal Hold": "regulated",
            "Journal": "regulated",
            "Orphaned": "general",
            "File System": "general",
        }.get(name, "general")
        return RetentionPolicy(
            name=name,
            retention_days=retention_days,
            classification=classification,
        )

    def _build_shortcut(
        self,
        *,
        shortcut_id: str,
        original_source_item_id: str,
        archive_id: str,
        original_path: str,
        created_at: datetime,
        archived_content_reference: str,
        status: str,
    ) -> Shortcut:
        """Build a deterministic shortcut for mixed datasets."""

        return Shortcut(
            target_path=original_path,
            description=f"Shortcut for {original_source_item_id}",
            shortcut_id=shortcut_id,
            original_source_item_id=original_source_item_id,
            archive_id=archive_id,
            original_path=original_path,
            created_at=created_at,
            archived_content_reference=archived_content_reference,
            status=status,
        )

    def _build_archived_file(
        self,
        *,
        path: str,
        size_bytes: int,
        checksum: str,
        file_name: str,
        extension: str,
        archived_at: datetime,
        modified_at: datetime,
        retention_policy: RetentionPolicy,
        legal_hold: bool,
        legal_hold_policy_id: str | None,
        source_path: str,
        shortcut: Shortcut | None,
    ) -> ArchivedFile:
        """Build a deterministic archived file for mixed datasets."""

        return ArchivedFile(
            path=path,
            size_bytes=size_bytes,
            checksum=checksum,
            file_name=file_name,
            extension=extension,
            archived_at=archived_at,
            modified_at=modified_at,
            legal_hold=legal_hold,
            legal_hold_policy_id=legal_hold_policy_id,
            source_path=source_path,
            shortcut=shortcut,
            retention_policy=retention_policy,
        )


__all__: list[str] = [
    "DatasetGenerator",
    "DatasetProfile",
    "LARGE_PROFILE",
    "MEDIUM_PROFILE",
    "SMALL_PROFILE",
]
