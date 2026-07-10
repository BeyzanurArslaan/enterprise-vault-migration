"""Fixture loader for the mock Enterprise Vault subsystem.

This module reads JSON fixtures used by the mock dataset generators and
converts them into typed records.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast


@dataclass(frozen=True, slots=True)
class UserFixture:
    """Typed representation of a user fixture record."""

    id: str
    name: str
    department: str


@dataclass(frozen=True, slots=True)
class DepartmentFixture:
    """Typed representation of a department fixture record."""

    name: str
    manager: str


@dataclass(frozen=True, slots=True)
class RetentionPolicyFixture:
    """Typed representation of a retention policy fixture record."""

    name: str
    retention_days: int
    classification: str


class FixtureLoader:
    """Load typed fixture records from the mock Enterprise Vault fixture files."""

    def __init__(self, fixtures_dir: Path | None = None) -> None:
        """Create a loader rooted at the repository fixture directory."""

        self._fixtures_dir = fixtures_dir or Path(__file__).resolve().parents[1] / "fixtures"
        self._users: tuple[UserFixture, ...] | None = None
        self._departments: tuple[DepartmentFixture, ...] | None = None
        self._mail_subjects: tuple[str, ...] | None = None
        self._attachment_names: tuple[str, ...] | None = None
        self._retention_policies: tuple[RetentionPolicyFixture, ...] | None = None

    def load_users(self) -> tuple[UserFixture, ...]:
        """Return all user fixture records."""

        if self._users is None:
            raw_users = cast(list[dict[str, object]], self._read_json("users.json"))
            self._users = tuple(
                UserFixture(
                    id=str(item["id"]),
                    name=str(item["name"]),
                    department=str(item["department"]),
                )
                for item in raw_users
            )

        return self._users

    def load_departments(self) -> tuple[DepartmentFixture, ...]:
        """Return all department fixture records."""

        if self._departments is None:
            raw_departments = cast(list[dict[str, object]], self._read_json("departments.json"))
            self._departments = tuple(
                DepartmentFixture(
                    name=str(item["name"]),
                    manager=str(item["manager"]),
                )
                for item in raw_departments
            )

        return self._departments

    def load_mail_subjects(self) -> tuple[str, ...]:
        """Return all mail subject fixture values."""

        if self._mail_subjects is None:
            self._mail_subjects = tuple(cast(list[str], self._read_json("mail_subjects.json")))

        return self._mail_subjects

    def load_attachment_names(self) -> tuple[str, ...]:
        """Return all attachment filename fixture values."""

        if self._attachment_names is None:
            self._attachment_names = tuple(
                cast(list[str], self._read_json("attachment_names.json"))
            )

        return self._attachment_names

    def load_retention_policies(self) -> tuple[RetentionPolicyFixture, ...]:
        """Return all retention policy fixture records."""

        if self._retention_policies is None:
            raw_policies = cast(list[dict[str, object]], self._read_json("retention_policies.json"))
            self._retention_policies = tuple(
                RetentionPolicyFixture(
                    name=str(item["name"]),
                    retention_days=cast(int, item["retention_days"]),
                    classification=str(item["classification"]),
                )
                for item in raw_policies
            )

        return self._retention_policies

    def _read_json(self, filename: str) -> Any:
        """Read and decode a fixture JSON file."""

        fixture_path = self._fixtures_dir / filename
        with fixture_path.open("r", encoding="utf-8") as handle:
            return json.load(handle)


__all__: list[str] = [
    "DepartmentFixture",
    "FixtureLoader",
    "RetentionPolicyFixture",
    "UserFixture",
]
