"""Mail item entity for the Enterprise Vault domain.

This module defines the mail item aggregate used to represent a message and
its associated content within the migration platform.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

from ..enums.migration_status import MigrationStatus
from ..value_objects.email_address import EmailAddress
from ..value_objects.identifiers import MailItemId
from .base import BaseEntity

if TYPE_CHECKING:
    from .attachment import Attachment
    from .retention_policy import RetentionPolicy


@dataclass(slots=True, kw_only=True)
class MailItem(BaseEntity):
    """Immutable structural representation of an Enterprise Vault mail item."""

    id: MailItemId
    subject: str
    sender: EmailAddress
    recipients: list[EmailAddress] = field(default_factory=list)
    sent_at: datetime
    received_at: datetime
    body: str
    attachments: list["Attachment"] = field(default_factory=list)
    retention_policy: "RetentionPolicy"
    migration_status: MigrationStatus


__all__: list[str] = ["MailItem"]
