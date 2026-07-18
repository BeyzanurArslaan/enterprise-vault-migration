"""Structured error breakdown helpers for the migration engine.

This module converts the immutable execution context and stage results into a
security-safe, deterministic audit trail of terminal migration failures. The
helpers never expose raw exception objects, stack traces, payload content, or
infrastructure-specific types. They only surface stable identifiers and
target-neutral classification data suitable for reports and exports.
"""

from __future__ import annotations

from ..contracts import ErrorBreakdownEntry, SourceMailItem
from ..step_context import MigrationStepContext
from ..transformation import TransformedDocument

_TRANSFORMATION_STAGE = "transformation"
_UPLOAD_STAGE = "upload"
_VERIFICATION_STAGE = "verification"
_PIPELINE_STAGE = "pipeline"


def build_error_breakdown_entries(
    context: MigrationStepContext,
    *,
    final_status: str,
    failed_step_name: str | None = None,
    retryable: bool = False,
    attempt_count: int = 1,
    failure_message: str | None = None,
) -> tuple[ErrorBreakdownEntry, ...]:
    """Build deterministic terminal error entries for an execution report.

    The function derives item-level failures from structured stage results and
    only falls back to a generic pipeline entry when no stage-level failure can
    be identified. This keeps successful retries, dry-run skips, and filtered
    items out of the final audit trail.
    """

    entries: list[ErrorBreakdownEntry] = []
    entries.extend(_build_transformation_entries(context, final_status=final_status))
    entries.extend(_build_upload_entries(context, final_status=final_status))
    entries.extend(_build_verification_entries(context, final_status=final_status))

    if not entries and failed_step_name is not None:
        entries.append(
            _build_pipeline_entry(
                context,
                final_status=final_status,
                failed_step_name=failed_step_name,
                retryable=retryable,
                attempt_count=attempt_count,
                failure_message=failure_message,
            ),
        )

    return tuple(entries)


def _build_transformation_entries(
    context: MigrationStepContext,
    *,
    final_status: str,
) -> tuple[ErrorBreakdownEntry, ...]:
    """Build error entries for failed transformation items."""

    transformation_result = context.transformation_result
    if transformation_result is None or not transformation_result.failed_item_identifiers:
        return ()

    entries: list[ErrorBreakdownEntry] = []
    for source_identifier in transformation_result.failed_item_identifiers:
        mail_item = _find_source_mail_item(context, source_identifier)
        archive_identifier, item_type = _resolve_source_mail_item_metadata(context, mail_item)
        entries.append(
            ErrorBreakdownEntry(
                source_identifier=source_identifier,
                stage=_TRANSFORMATION_STAGE,
                category="transformation",
                code="transformation_failed",
                message="Transformation failed for a source item.",
                retryable=False,
                attempt_count=1,
                final_status=final_status,
                archive_identifier=archive_identifier,
                item_type=item_type,
            ),
        )

    return tuple(entries)


def _build_upload_entries(
    context: MigrationStepContext,
    *,
    final_status: str,
) -> tuple[ErrorBreakdownEntry, ...]:
    """Build error entries for failed upload items."""

    upload_result = context.upload_result
    if upload_result is None or not upload_result.failed_documents:
        return ()

    entries: list[ErrorBreakdownEntry] = []
    for document in upload_result.failed_documents:
        entries.append(
            ErrorBreakdownEntry(
                source_identifier=document.source_identifier,
                stage=_UPLOAD_STAGE,
                category="upload",
                code="upload_failed",
                message="Upload failed for a transformed document.",
                retryable=False,
                attempt_count=1,
                final_status=final_status,
                archive_identifier=document.archive_name,
                item_type=str(document.item_type),
            ),
        )

    return tuple(entries)


def _build_verification_entries(
    context: MigrationStepContext,
    *,
    final_status: str,
) -> tuple[ErrorBreakdownEntry, ...]:
    """Build error entries for failed verification items."""

    verification_result = context.verification_result
    if verification_result is None:
        return ()

    transformed_documents = _transformed_document_map(context)
    ordered_ids: list[str] = []
    failure_reasons: dict[str, set[str]] = {}

    def record(source_identifier: str, reason: str) -> None:
        if source_identifier not in failure_reasons:
            ordered_ids.append(source_identifier)
            failure_reasons[source_identifier] = set()

        failure_reasons[source_identifier].add(reason)

    for source_identifier in verification_result.failed_document_ids:
        record(source_identifier, "failed")
    for source_identifier in verification_result.missing_document_ids:
        record(source_identifier, "missing")
    for source_identifier in verification_result.checksum_mismatches:
        record(source_identifier, "checksum")
    for source_identifier in verification_result.metadata_mismatches:
        record(source_identifier, "metadata")

    if not ordered_ids:
        return ()

    entries: list[ErrorBreakdownEntry] = []
    for source_identifier in ordered_ids:
        reasons = failure_reasons[source_identifier]
        document = transformed_documents.get(source_identifier)
        archive_identifier = document.archive_name if document is not None else None
        item_type = str(document.item_type) if document is not None else None
        code, message = _resolve_verification_failure(reasons)
        entries.append(
            ErrorBreakdownEntry(
                source_identifier=source_identifier,
                stage=_VERIFICATION_STAGE,
                category="verification",
                code=code,
                message=message,
                retryable=False,
                attempt_count=1,
                final_status=final_status,
                archive_identifier=archive_identifier,
                item_type=item_type,
            ),
        )

    return tuple(entries)


def _build_pipeline_entry(
    context: MigrationStepContext,
    *,
    final_status: str,
    failed_step_name: str,
    retryable: bool,
    attempt_count: int,
    failure_message: str | None,
) -> ErrorBreakdownEntry:
    """Build a fallback entry for an unrecoverable pipeline step failure."""

    current_archive = None
    if context.progress_tracker is not None:
        current_archive = context.progress_tracker.current_snapshot.current_archive

    return ErrorBreakdownEntry(
        source_identifier=None,
        stage=failed_step_name,
        category=_PIPELINE_STAGE,
        code="step_failed",
        message=failure_message or "Pipeline step failed.",
        retryable=retryable,
        attempt_count=attempt_count,
        final_status=final_status,
        archive_identifier=current_archive,
        item_type=None,
    )


def _resolve_verification_failure(reasons: set[str]) -> tuple[str, str]:
    """Resolve a stable code/message pair for a verification failure."""

    if "missing" in reasons:
        if reasons == {"missing"}:
            return "missing_document", "Target document was missing during verification."
        return "verification_failed", "Verification failed due to a missing document."

    if "checksum" in reasons:
        if reasons == {"checksum"}:
            return "checksum_mismatch", "Target document checksum mismatched during verification."
        return "verification_failed", "Verification failed due to a checksum mismatch."

    if "metadata" in reasons:
        if reasons == {"metadata"}:
            return "metadata_mismatch", "Target document metadata mismatched during verification."
        return "verification_failed", "Verification failed due to a metadata mismatch."

    return "verification_failed", "Verification failed during target comparison."


def _transformed_document_map(
    context: MigrationStepContext,
) -> dict[str, TransformedDocument]:
    """Build a lookup of transformed documents by source identifier."""

    transformation_result = context.transformation_result
    if transformation_result is None:
        return {}

    return {
        document.source_identifier: document
        for document in transformation_result.transformed_documents
    }


def _find_source_mail_item(
    context: MigrationStepContext,
    source_identifier: str,
) -> SourceMailItem | None:
    """Find a source mail item by its stable identifier."""

    extraction_result = context.extraction_result
    if extraction_result is None:
        return None

    for mail_item in extraction_result.extracted_mail_items:
        if mail_item.internet_message_id == source_identifier:
            return mail_item

    return None


def _resolve_source_mail_item_metadata(
    context: MigrationStepContext,
    mail_item: SourceMailItem | None,
) -> tuple[str | None, str | None]:
    """Resolve archive and item type metadata for a source mail item."""

    if mail_item is None:
        return None, None

    item_type = str(mail_item.item_type)
    if context.vault_stores is None:
        return None, item_type

    for vault_store in context.vault_stores:
        for archive in vault_store.archives:
            for mailbox in archive.mailboxes:
                for candidate in mailbox.mail_items:
                    if candidate is mail_item or (
                        candidate.internet_message_id == mail_item.internet_message_id
                    ):
                        return archive.name, item_type
            for journal_archive in archive.journal_archives:
                for candidate in journal_archive.mail_items:
                    if candidate is mail_item or (
                        candidate.internet_message_id == mail_item.internet_message_id
                    ):
                        return archive.name, item_type

    return None, item_type


__all__: list[str] = ["build_error_breakdown_entries"]
