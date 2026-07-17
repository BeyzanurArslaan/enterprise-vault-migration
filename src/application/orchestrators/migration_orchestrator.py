"""Compatibility facade for the canonical migration orchestrator.

This module preserves the historical application-layer import path while
re-exporting the concrete orchestrator implemented in the migration engine.
The facade does not introduce a second orchestration implementation.
"""

from __future__ import annotations

from migration_engine.orchestrator import MigrationOrchestrator

__all__: list[str] = ["MigrationOrchestrator"]
