"""Attachment generator for the mock Enterprise Vault subsystem.

This module produces synthetic attachment entities using the shared
deterministic generation context.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Final

from mock_ev.builders import AttachmentBuilder
from mock_ev.entities import Attachment
from mock_ev.loaders import FixtureLoader

from ._shared import GenerationContext, build_generation_context

_MIME_TYPES: Final[dict[str, str]] = {
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "pdf": "application/pdf",
    "png": "image/png",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}

_SIZE_RANGES: Final[dict[str, tuple[int, int]]] = {
    "docx": (16_384, 1_048_576),
    "pdf": (32_768, 5_242_880),
    "png": (8_192, 3_145_728),
    "pptx": (65_536, 10_485_760),
    "xlsx": (16_384, 2_097_152),
}


class AttachmentGenerator:
    """Generate synthetic attachment entities."""

    def __init__(
        self,
        context: GenerationContext | None = None,
        *,
        seed: int | None = None,
        loader: FixtureLoader | None = None,
        builder: AttachmentBuilder | None = None,
    ) -> None:
        """Create a generator bound to the shared deterministic context."""

        self._context = context or build_generation_context(seed, loader or FixtureLoader())
        self._builder = builder or AttachmentBuilder()

    def generate_one(
        self,
        *,
        filename: str | None = None,
        name: str | None = None,
        mime_type: str | None = None,
        content_type: str | None = None,
        size_bytes: int | None = None,
        size: int | None = None,
    ) -> Attachment:
        """Generate a single attachment entity."""

        selected_filename = filename or name or self._choose_filename()
        selected_extension = Path(selected_filename).suffix.lower().lstrip(".")
        selected_mime_type = (
            mime_type
            or content_type
            or _MIME_TYPES.get(selected_extension, "application/octet-stream")
        )
        selected_size = size_bytes if size_bytes is not None else size
        if selected_size is None:
            selected_size = self._choose_size(selected_extension)
        checksum = hashlib.sha256(
            f"{selected_filename}|{selected_extension}|{selected_mime_type}|{selected_size}".encode()
        ).hexdigest()

        return self._builder.build(
            filename=selected_filename,
            extension=selected_extension,
            mime_type=selected_mime_type,
            size_bytes=selected_size,
            checksum=checksum,
        )

    def generate_many(self, count: int) -> list[Attachment]:
        """Generate multiple attachments in sequence."""

        return [self.generate_one() for _ in range(count)]

    def _choose_filename(self) -> str:
        """Select a deterministic fixture-backed attachment name."""

        return self._context.rng.choice(self._context.attachment_names)

    def _choose_size(self, extension: str) -> int:
        """Select a realistic attachment size for the given extension."""

        lower_bound, upper_bound = _SIZE_RANGES.get(extension, (4_096, 1_048_576))
        return self._context.rng.randint(lower_bound, upper_bound)


__all__: list[str] = ["AttachmentGenerator"]
