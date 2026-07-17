"""Migration engine contracts package.

This package defines the abstraction layer used by the migration execution
pipeline. The current sprint establishes immutable context and reporting
contracts together with the abstract pipeline step interface.
"""

from __future__ import annotations

from .execution_context import ExecutionContext
from .execution_report import ExecutionReport
from .pipeline_step import PipelineStep
from .progress_snapshot import ProgressSnapshot
from .source_models import (
    SourceArchive,
    SourceArchivedFile,
    SourceAttachment,
    SourceContentPart,
    SourceDatasetGenerator,
    SourceJournalArchive,
    SourceMailbox,
    SourceMailItem,
    SourceRetentionPolicy,
    SourceShortcut,
    SourceVaultStore,
)

__all__: list[str] = [
    "ExecutionContext",
    "ExecutionReport",
    "PipelineStep",
    "ProgressSnapshot",
    "SourceArchive",
    "SourceArchivedFile",
    "SourceAttachment",
    "SourceContentPart",
    "SourceDatasetGenerator",
    "SourceJournalArchive",
    "SourceMailbox",
    "SourceMailItem",
    "SourceRetentionPolicy",
    "SourceShortcut",
    "SourceVaultStore",
]
