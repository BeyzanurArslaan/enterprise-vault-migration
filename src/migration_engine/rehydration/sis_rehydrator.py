"""SIS rehydration service for the migration engine.

This module reconstructs source item content from SIS content parts using an
execution-scoped deterministic cache. Each validated part is cached by stable
part identifier so repeated rehydration calls within the same run can reuse
previously validated bytes without repeating integrity checks. The service
raises structural validation errors when a part is missing, malformed, or
inconsistent with its declared metadata.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime

from domain.exceptions import ValidationError

from ..contracts import SourceContentPart, SourceMailItem
from .rehydrated_content import RehydratedContent


@dataclass(slots=True, frozen=True)
class _CachedContentPart:
    """Validated SIS content part stored in the execution-scoped cache."""

    part_id: str
    data_ref: str
    data: bytes
    size_bytes: int
    sha256: str


class SisRehydrator:
    """Rehydrate source mail item content from validated SIS parts."""

    def __init__(self) -> None:
        """Create an empty execution-scoped SIS rehydration cache."""

        self._cache: dict[str, _CachedContentPart] = {}
        self._rehydrated_items = 0
        self._rehydration_failures = 0
        self._rehydrated_bytes = 0
        self._cache_hits = 0
        self._cache_misses = 0

    @property
    def rehydrated_items(self) -> int:
        """Return the number of successfully rehydrated items."""

        return self._rehydrated_items

    @property
    def rehydration_failures(self) -> int:
        """Return the number of failed rehydration attempts."""

        return self._rehydration_failures

    @property
    def rehydrated_bytes(self) -> int:
        """Return the total bytes rebuilt by the service."""

        return self._rehydrated_bytes

    @property
    def cache_hits(self) -> int:
        """Return the number of cache hits served by the rehydrator."""

        return self._cache_hits

    @property
    def cache_misses(self) -> int:
        """Return the number of cache misses recorded by the rehydrator."""

        return self._cache_misses

    def rehydrate(
        self,
        mail_item: SourceMailItem,
        *,
        started_at: datetime,
        completed_at: datetime,
    ) -> RehydratedContent:
        """Rebuild a source item payload from ordered SIS content parts."""

        try:
            content_parts = tuple(mail_item.content_parts)
            if len(content_parts) == 0:
                content_bytes = mail_item.body.encode("utf-8")
                checksum = hashlib.sha256(content_bytes).hexdigest()
                self._rehydrated_items += 1
                self._rehydrated_bytes += len(content_bytes)
                return RehydratedContent(
                    source_identifier=mail_item.internet_message_id,
                    content_bytes=content_bytes,
                    content_parts=content_parts,
                    checksum=checksum,
                    size_bytes=len(content_bytes),
                    started_at=started_at,
                    completed_at=completed_at,
                )

            content_bytes = b"".join(
                self._resolve_content_part(part).data for part in content_parts
            )
            checksum = hashlib.sha256(content_bytes).hexdigest()
            self._rehydrated_items += 1
            self._rehydrated_bytes += len(content_bytes)
            return RehydratedContent(
                source_identifier=mail_item.internet_message_id,
                content_bytes=content_bytes,
                content_parts=content_parts,
                checksum=checksum,
                size_bytes=len(content_bytes),
                started_at=started_at,
                completed_at=completed_at,
            )
        except Exception:
            self._rehydration_failures += 1
            raise

    def _resolve_content_part(self, content_part: SourceContentPart) -> _CachedContentPart:
        """Validate and cache a single SIS content part."""

        cached_part = self._cache.get(content_part.part_id)
        if cached_part is not None:
            if not self._matches_cache(cached_part, content_part):
                message = (
                    f"Cached SIS content part {content_part.part_id!r} does not match "
                    "the supplied metadata."
                )
                raise ValidationError(message)

            self._cache_hits += 1
            return cached_part

        validated_part = self._validate_content_part(content_part)
        self._cache[validated_part.part_id] = validated_part
        self._cache_misses += 1
        return validated_part

    def _validate_content_part(self, content_part: SourceContentPart) -> _CachedContentPart:
        """Validate the integrity of a SIS content part before caching it."""

        if not content_part.part_id:
            message = "SIS content part requires a stable part identifier"
            raise ValidationError(message)
        if not content_part.data_ref:
            message = f"SIS content part {content_part.part_id!r} requires a data reference"
            raise ValidationError(message)
        if content_part.size_bytes < 0:
            message = f"SIS content part {content_part.part_id!r} cannot have negative size"
            raise ValidationError(message)

        actual_size = len(content_part.data)
        if actual_size != content_part.size_bytes:
            message = (
                f"SIS content part {content_part.part_id!r} reported size "
                f"{content_part.size_bytes} but contains {actual_size} bytes"
            )
            raise ValidationError(message)

        actual_checksum = hashlib.sha256(content_part.data).hexdigest()
        if actual_checksum != content_part.sha256:
            message = (
                f"SIS content part {content_part.part_id!r} reported checksum "
                f"{content_part.sha256!r} but contains {actual_checksum!r}"
            )
            raise ValidationError(message)

        return _CachedContentPart(
            part_id=content_part.part_id,
            data_ref=content_part.data_ref,
            data=content_part.data,
            size_bytes=content_part.size_bytes,
            sha256=content_part.sha256,
        )

    def _matches_cache(
        self,
        cached_part: _CachedContentPart,
        content_part: SourceContentPart,
    ) -> bool:
        """Return whether a cached SIS part still matches the requested metadata."""

        return (
            cached_part.part_id == content_part.part_id
            and cached_part.data_ref == content_part.data_ref
            and cached_part.size_bytes == content_part.size_bytes
            and cached_part.sha256 == content_part.sha256
            and cached_part.data == content_part.data
        )


__all__: list[str] = ["SisRehydrator"]
