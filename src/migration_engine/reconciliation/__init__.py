"""Reconciliation contracts for the migration engine.

This package exposes the neutral reconciliation result model used by the
finalization step to compare transformed source scope with the observed target
outcome. The contract remains behavior-free and target-neutral.
"""

from __future__ import annotations

from .reconciliation_result import ReconciliationResult

__all__: list[str] = ["ReconciliationResult"]
