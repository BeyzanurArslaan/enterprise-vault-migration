"""Loader package for the mock Enterprise Vault subsystem.

This package provides typed readers for the JSON fixtures that seed synthetic
Enterprise Vault datasets.
"""

from __future__ import annotations

from .fixture_loader import DepartmentFixture, FixtureLoader, RetentionPolicyFixture, UserFixture

__all__: list[str] = [
    "DepartmentFixture",
    "FixtureLoader",
    "RetentionPolicyFixture",
    "UserFixture",
]
