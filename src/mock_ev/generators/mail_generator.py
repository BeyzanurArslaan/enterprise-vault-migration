"""Mail generator for the mock Enterprise Vault subsystem.

This module produces synthetic mail items, including message metadata,
recipients, body text, timestamps, and generated attachments.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import Final

from mock_ev.builders import MailDatasetBuilder
from mock_ev.entities import Attachment, MailItem, RetentionPolicy
from mock_ev.loaders import FixtureLoader

from ._shared import GenerationContext, build_generation_context
from .attachment_generator import AttachmentGenerator

_MAIL_WINDOW_START: Final[datetime] = datetime(2024, 1, 1, tzinfo=UTC)
_MAIL_WINDOW_END: Final[datetime] = datetime(2025, 12, 31, 23, 59, 59, tzinfo=UTC)


class MailGenerator:
    """Generate synthetic mail item entities."""

    def __init__(
        self,
        context: GenerationContext | None = None,
        *,
        seed: int | None = None,
        loader: FixtureLoader | None = None,
        attachment_generator: AttachmentGenerator | None = None,
        builder: MailDatasetBuilder | None = None,
    ) -> None:
        """Create a generator bound to the shared deterministic context."""

        self._context = context or build_generation_context(seed, loader or FixtureLoader())
        self._attachment_generator = attachment_generator or AttachmentGenerator(self._context)
        self._builder = builder or MailDatasetBuilder()

    def generate_one(self, *, attachment_count: int) -> MailItem:
        """Generate a single mail item."""

        subject = self._context.rng.choice(self._context.mail_subjects)
        sender = self._context.rng.choice(self._context.contact_emails)
        body = self._context.faker.paragraph(nb_sentences=self._context.rng.randint(3, 7))
        recipients = self._choose_addresses(exclude=sender, minimum=1, maximum=4)
        cc_recipients = self._choose_addresses(
            exclude=sender,
            minimum=0,
            maximum=2,
            avoid=recipients,
        )
        bcc_recipients = self._choose_addresses(
            exclude=sender,
            minimum=0,
            maximum=2,
            avoid=recipients + cc_recipients,
        )
        attachments = self._attachment_generator.generate_many(attachment_count)
        received_at = self._context.faker.date_time_between(
            start_date=_MAIL_WINDOW_START,
            end_date=_MAIL_WINDOW_END,
            tzinfo=UTC,
        )
        sent_at = self._context.faker.date_time_between(
            start_date=received_at - timedelta(hours=12),
            end_date=received_at - timedelta(minutes=1),
            tzinfo=UTC,
        )
        modified_at = self._context.faker.date_time_between(
            start_date=received_at,
            end_date=received_at + timedelta(hours=24),
            tzinfo=UTC,
        )
        internet_message_id = f"<{self._context.faker.uuid4()}@{self._sender_domain(sender)}>"
        conversation_id = self._context.faker.uuid4()
        retention_policy = self._choose_retention_policy()
        message_size = self._calculate_message_size(
            body=body,
            subject=subject,
            recipients=recipients,
            cc_recipients=cc_recipients,
            bcc_recipients=bcc_recipients,
            attachments=attachments,
        )

        return self._builder.build(
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
            recipients=recipients,
            cc_recipients=cc_recipients,
            bcc_recipients=bcc_recipients,
            attachments=attachments,
        )

    def _choose_addresses(
        self,
        *,
        exclude: str,
        minimum: int,
        maximum: int,
        avoid: Sequence[str] = (),
    ) -> list[str]:
        """Choose a deterministic list of unique addresses."""

        available_addresses = [
            address
            for address in self._context.contact_emails
            if address != exclude and address not in avoid
        ]
        if not available_addresses:
            return []

        upper_bound = min(maximum, len(available_addresses))
        lower_bound = min(minimum, upper_bound)
        if upper_bound == 0:
            return []

        chosen_count = self._context.rng.randint(lower_bound, upper_bound)
        return self._context.rng.sample(available_addresses, chosen_count)

    def _choose_retention_policy(self) -> RetentionPolicy:
        """Convert a retention policy fixture into a domain entity."""

        fixture_policy = self._context.rng.choice(self._context.retention_policies)
        return RetentionPolicy(
            name=fixture_policy.name,
            retention_days=fixture_policy.retention_days,
            classification=fixture_policy.classification,
        )

    def _calculate_message_size(
        self,
        *,
        body: str,
        subject: str,
        recipients: Sequence[str],
        cc_recipients: Sequence[str],
        bcc_recipients: Sequence[str],
        attachments: Sequence[Attachment],
    ) -> int:
        """Calculate a realistic message size in bytes."""

        attachment_sizes = sum(attachment.size_bytes for attachment in attachments)
        overhead = (
            1_024 + (len(recipients) * 128) + (len(cc_recipients) * 64) + (len(bcc_recipients) * 64)
        )
        return len(body.encode()) + len(subject.encode()) + attachment_sizes + overhead

    def _sender_domain(self, sender: str) -> str:
        """Extract the sender domain for message identifier generation."""

        return sender.split("@", maxsplit=1)[-1]


__all__: list[str] = ["MailGenerator"]
