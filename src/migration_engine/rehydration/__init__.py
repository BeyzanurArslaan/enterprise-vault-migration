"""SIS rehydration package for the migration engine.

This package contains the target-neutral SIS rehydration contracts and the
execution-scoped cache-backed service used by the transformation step. The
package exposes only the minimal immutable result model and service needed to
rebuild source item content deterministically during a migration run.
"""

from __future__ import annotations

from .rehydrated_content import RehydratedContent
from .sis_rehydrator import SisRehydrator

__all__: list[str] = ["RehydratedContent", "SisRehydrator"]
