"""Regression tests for the migration extraction result contract."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest

from migration_engine.extraction import ExtractionResult
from mock_ev.entities import Archive, Attachment, Mailbox, MailItem, RetentionPolicy


def _build_result() -> ExtractionResult:
    """Create a sample extraction result for regression tests."""

    timestamp = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    retention_policy = RetentionPolicy(
        name="Standard",
        retention_days=30,
        classification="general",
    )
    attachment = Attachment(
        filename="report.txt",
        extension="txt",
        mime_type="text/plain",
        size_bytes=32,
        checksum="checksum-1",
    )
    mail_item = MailItem(
        subject="Test message",
        sender="sender@example.com",
        body="Body",
        received_at=timestamp,
        sent_at=timestamp,
        modified_at=timestamp,
        internet_message_id="message-1",
        conversation_id="conversation-1",
        message_size=128,
        retention_policy=retention_policy,
        attachments=[attachment],
    )
    mailbox = Mailbox(address="mailbox@example.com", mail_items=[mail_item])
    archive = Archive(name="Archive 1", mailboxes=[mailbox])

    return ExtractionResult(
        discovered_archives=(archive,),
        extracted_mailboxes=(mailbox,),
        extracted_mail_items=(mail_item,),
        extracted_attachments=(attachment,),
        total_mailboxes=1,
        total_items=1,
        total_attachments=1,
    )


def test_extraction_result_is_immutable_and_structural() -> None:
    """The extraction result should remain an immutable structural contract."""

    result = _build_result()

    assert len(result.discovered_archives) == 1
    assert len(result.extracted_mailboxes) == 1
    assert len(result.extracted_mail_items) == 1
    assert len(result.extracted_attachments) == 1
    assert result.total_mailboxes == 1
    assert result.total_items == 1
    assert result.total_attachments == 1

    with pytest.raises(FrozenInstanceError):
        type(result).__setattr__(result, "total_items", 2)
