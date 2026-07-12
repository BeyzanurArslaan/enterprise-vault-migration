"""Migration engine step package.

This package groups the concrete pipeline step skeletons used by the migration
engine execution flow. The current sprint establishes the class structure only
and intentionally leaves all step behavior unimplemented.
"""

from __future__ import annotations

from .discover_archives_step import DiscoverArchivesStep
from .extract_items_step import ExtractItemsStep
from .finalize_migration_step import FinalizeMigrationStep
from .transform_items_step import TransformItemsStep
from .upload_items_step import UploadItemsStep
from .verify_items_step import VerifyItemsStep

__all__: list[str] = [
    "DiscoverArchivesStep",
    "ExtractItemsStep",
    "FinalizeMigrationStep",
    "TransformItemsStep",
    "UploadItemsStep",
    "VerifyItemsStep",
]
