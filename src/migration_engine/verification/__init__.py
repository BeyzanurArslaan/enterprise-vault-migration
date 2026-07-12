"""Verification contracts package for the migration engine foundation.

This package defines immutable verification outputs used by the migration
engine orchestration layer during post-upload target validation.
"""

from __future__ import annotations

from .verification_result import VerificationResult

__all__: list[str] = ["VerificationResult"]
