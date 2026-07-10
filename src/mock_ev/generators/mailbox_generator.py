"""Mailbox generator for the mock Enterprise Vault subsystem.

This module produces synthetic mailbox entities and their contained mail
items.
"""

from __future__ import annotations

from collections.abc import Sequence

from mock_ev.builders import MailboxBuilder
from mock_ev.entities import Mailbox
from mock_ev.loaders import FixtureLoader

from ._shared import GenerationContext, build_generation_context
from .mail_generator import MailGenerator


class MailboxGenerator:
    """Generate synthetic mailbox entities."""

    def __init__(
        self,
        context: GenerationContext | None = None,
        *,
        seed: int | None = None,
        loader: FixtureLoader | None = None,
        mail_generator: MailGenerator | None = None,
        builder: MailboxBuilder | None = None,
    ) -> None:
        """Create a generator bound to the shared deterministic context."""

        self._context = context or build_generation_context(seed, loader or FixtureLoader())
        self._mail_generator = mail_generator or MailGenerator(self._context)
        self._builder = builder or MailboxBuilder()

    def generate_one(
        self,
        *,
        attachment_counts: Sequence[int],
        address: str | None = None,
    ) -> Mailbox:
        """Generate a single mailbox populated with mail items."""

        selected_address = address or self._context.faker.company_email()
        mail_items = [
            self._mail_generator.generate_one(attachment_count=attachment_count)
            for attachment_count in attachment_counts
        ]
        return self._builder.build(address=selected_address, mail_items=mail_items)


__all__: list[str] = ["MailboxGenerator"]
