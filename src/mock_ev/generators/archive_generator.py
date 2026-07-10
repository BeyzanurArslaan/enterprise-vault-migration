"""Archive generator for the mock Enterprise Vault subsystem.

This module produces synthetic archive entities and their contained mailboxes.
"""

from __future__ import annotations

from collections.abc import Sequence

from mock_ev.builders import ArchiveBuilder
from mock_ev.entities import Archive
from mock_ev.loaders import FixtureLoader

from ._shared import GenerationContext, build_generation_context
from .mailbox_generator import MailboxGenerator


class ArchiveGenerator:
    """Generate synthetic archive entities."""

    def __init__(
        self,
        context: GenerationContext | None = None,
        *,
        seed: int | None = None,
        loader: FixtureLoader | None = None,
        mailbox_generator: MailboxGenerator | None = None,
        builder: ArchiveBuilder | None = None,
    ) -> None:
        """Create a generator bound to the shared deterministic context."""

        self._context = context or build_generation_context(seed, loader or FixtureLoader())
        self._mailbox_generator = mailbox_generator or MailboxGenerator(self._context)
        self._builder = builder or ArchiveBuilder()

    def generate_one(
        self,
        *,
        mailbox_attachment_counts: Sequence[Sequence[int]],
        name: str | None = None,
    ) -> Archive:
        """Generate a single archive populated with mailboxes."""

        selected_name = name or f"{self._context.faker.company()} Archive"
        mailboxes = [
            self._mailbox_generator.generate_one(attachment_counts=attachment_counts)
            for attachment_counts in mailbox_attachment_counts
        ]
        return self._builder.build(name=selected_name, mailboxes=mailboxes)


__all__: list[str] = ["ArchiveGenerator"]
