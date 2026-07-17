"""Mail item entity for the mock Enterprise Vault subsystem.

This module defines the structural representation of a simulated mail item
used by the mock dataset generators.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

from domain.enums.item_type import ItemType

if TYPE_CHECKING:
    from .attachment import Attachment
    from .content_part import ContentPart
    from .retention_policy import RetentionPolicy


@dataclass(slots=True, kw_only=True)
class MailItem:
    """Structural representation of a mock mail item within a mailbox."""

    subject: str
    sender: str
    body: str
    received_at: datetime
    sent_at: datetime
    modified_at: datetime
    internet_message_id: str
    conversation_id: str
    message_size: int
    retention_policy: RetentionPolicy
    item_type: ItemType = ItemType.EMAIL
    recipients: list[str] = field(default_factory=list)
    cc_recipients: list[str] = field(default_factory=list)
    bcc_recipients: list[str] = field(default_factory=list)
    attachments: list[Attachment] = field(default_factory=list)
    content_parts: list[ContentPart] = field(default_factory=list)
    folder_path: str = "/Inbox"
    legal_hold: bool = False
    legal_hold_policy_id: str | None = None
    journal_metadata: tuple[tuple[str, str], ...] = ()
    source_path: str | None = None


__all__: list[str] = ["MailItem"]
