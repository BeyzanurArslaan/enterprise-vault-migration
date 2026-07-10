"""Shared utilities for the mock Enterprise Vault generators.

This module contains the deterministic generation context and small helper
functions used by the generator layer.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from random import Random

from faker import Faker

from mock_ev.loaders import (
    DepartmentFixture,
    FixtureLoader,
    RetentionPolicyFixture,
    UserFixture,
)


@dataclass(slots=True)
class GenerationContext:
    """Hold the shared random state and loaded fixtures for a dataset run."""

    seed: int | None
    rng: Random
    faker: Faker
    users: tuple[UserFixture, ...]
    departments: tuple[DepartmentFixture, ...]
    mail_subjects: tuple[str, ...]
    attachment_names: tuple[str, ...]
    retention_policies: tuple[RetentionPolicyFixture, ...]
    contact_emails: tuple[str, ...]


def build_generation_context(seed: int | None, loader: FixtureLoader) -> GenerationContext:
    """Build a deterministic generation context from fixtures and seed state."""

    rng = Random(seed)
    faker = Faker()
    if seed is not None:
        faker.seed_instance(seed)

    users = loader.load_users()
    departments = loader.load_departments()
    mail_subjects = loader.load_mail_subjects()
    attachment_names = loader.load_attachment_names()
    retention_policies = loader.load_retention_policies()
    contact_emails = _build_contact_emails(
        faker=faker,
        rng=rng,
        users=users,
        departments=departments,
    )

    return GenerationContext(
        seed=seed,
        rng=rng,
        faker=faker,
        users=users,
        departments=departments,
        mail_subjects=mail_subjects,
        attachment_names=attachment_names,
        retention_policies=retention_policies,
        contact_emails=contact_emails,
    )


def distribute(total: int, buckets: int, rng: Random) -> list[int]:
    """Distribute ``total`` items across ``buckets`` buckets as evenly as possible."""

    if buckets <= 0:
        raise ValueError("buckets must be positive")
    if total < buckets:
        raise ValueError("total must be at least buckets")

    counts = [total // buckets for _ in range(buckets)]
    for index in range(total % buckets):
        counts[index] += 1

    rng.shuffle(counts)
    return counts


def _build_contact_emails(
    *,
    faker: Faker,
    rng: Random,
    users: Sequence[UserFixture],
    departments: Sequence[DepartmentFixture],
    size: int = 200,
) -> tuple[str, ...]:
    """Create a deterministic pool of sender and recipient addresses."""

    emails = [_user_email(user) for user in users]
    emails.extend(
        f"{_slugify(department.name)}@corporate.example.com" for department in departments
    )
    while len(emails) < size:
        emails.append(faker.email())

    rng.shuffle(emails)
    return tuple(emails)


def _user_email(user: UserFixture) -> str:
    """Derive an email address from a fixture user record."""

    local_part = _slugify(user.name)
    domain_part = _slugify(user.department)
    return f"{local_part}@{domain_part}.example.com"


def _slugify(value: str) -> str:
    """Convert a value into a lowercase email-safe slug."""

    slug = re.sub(r"[^a-z0-9]+", ".", value.lower()).strip(".")
    return slug or "example"
