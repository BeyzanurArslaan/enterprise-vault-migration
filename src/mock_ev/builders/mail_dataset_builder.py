"""Mail dataset builder for the mock Enterprise Vault subsystem.

This module defines the builder responsible for composing mock mail items that
can later be expanded into richer scenarios.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from mock_ev.entities import Attachment, MailItem, RetentionPolicy


class MailDatasetBuilder:
    """Build mock mail items from prepared metadata and attachments."""

    def build(
        self,
        *,
        subject: str,
        sender: str,
        body: str,
        received_at: datetime,
        sent_at: datetime,
        modified_at: datetime,
        internet_message_id: str,
        conversation_id: str,
        message_size: int,
        retention_policy: RetentionPolicy,
        recipients: Sequence[str] | None = None,
        cc_recipients: Sequence[str] | None = None,
        bcc_recipients: Sequence[str] | None = None,
        attachments: Sequence[Attachment] | None = None,
        folder_path: str = "/Inbox",
    ) -> MailItem:
        """Construct a mail item from already-built primitives."""

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
            recipients=list(recipients or []),
            cc_recipients=list(cc_recipients or []),
            bcc_recipients=list(bcc_recipients or []),
            attachments=list(attachments or []),
            folder_path=folder_path,
        )


__all__: list[str] = ["MailDatasetBuilder"]
