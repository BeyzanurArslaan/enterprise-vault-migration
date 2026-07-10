"""Dataset generator for the mock Enterprise Vault subsystem.

This module provides the public entry point for generating complete synthetic
Enterprise Vault vault store hierarchies.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, cast

from mock_ev.builders import EnterpriseVaultBuilder
from mock_ev.entities import Archive, VaultStore
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


__all__: list[str] = [
    "DatasetGenerator",
    "DatasetProfile",
    "LARGE_PROFILE",
    "MEDIUM_PROFILE",
    "SMALL_PROFILE",
]
