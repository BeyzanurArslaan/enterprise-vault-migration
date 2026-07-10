"""Mailbox entity for the mock Enterprise Vault subsystem.

This module defines the structural representation of a simulated mailbox.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .mail_item import MailItem


@dataclass(slots=True, kw_only=True)
class Mailbox:
    """Structural representation of a mock mailbox within an archive."""

    address: str
    mail_items: list[MailItem] = field(default_factory=list)


__all__: list[str] = ["Mailbox"]
