"""In-memory storage module for the mock storionX subsystem.

This module provides lightweight, infrastructure-independent storage classes
for the mock storionX target platform scaffold. The storages keep entities in
memory only and expose a minimal CRUD-style interface for development and
testing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import RLock
from typing import TypeVar

from mock_storionx.entities import Document, Folder, Metadata, UploadSession, Workspace

TEntity = TypeVar("TEntity")


@dataclass(slots=True)
class _InMemoryStorage[TEntity]:
    """Store entities in a dictionary keyed by their identifier."""

    _items: dict[str, TEntity] = field(default_factory=dict)
    _lock: RLock = field(default_factory=RLock, init=False, repr=False)

    def add(self, item: TEntity) -> TEntity:
        """Add an item to the in-memory storage."""

        with self._lock:
            self._items[self._key(item)] = item
            return item

    def get(self, identifier: str) -> TEntity | None:
        """Return an item by identifier when present."""

        with self._lock:
            return self._items.get(identifier)

    def list(self) -> list[TEntity]:
        """Return all stored items."""

        with self._lock:
            return list(self._items.values())

    def remove(self, identifier: str) -> None:
        """Remove an item by identifier when present."""

        with self._lock:
            self._items.pop(identifier, None)

    def _key(self, item: TEntity) -> str:
        """Extract the storage key for an item."""

        msg = "Subclasses must implement _key()."
        raise NotImplementedError(msg)


class WorkspaceStorage(_InMemoryStorage[Workspace]):
    """Store mock storionX workspace entities in memory."""

    def _key(self, item: Workspace) -> str:
        """Return the workspace identifier used as the storage key."""

        return item.id


class FolderStorage(_InMemoryStorage[Folder]):
    """Store mock storionX folder entities in memory."""

    def _key(self, item: Folder) -> str:
        """Return the folder identifier used as the storage key."""

        return item.id


class DocumentStorage(_InMemoryStorage[Document]):
    """Store mock storionX document entities in memory."""

    def _key(self, item: Document) -> str:
        """Return the document identifier used as the storage key."""

        return item.id


class UploadSessionStorage(_InMemoryStorage[UploadSession]):
    """Store mock storionX upload session entities in memory."""

    def _key(self, item: UploadSession) -> str:
        """Return the upload session identifier used as the storage key."""

        return item.id


class MetadataStorage(_InMemoryStorage[Metadata]):
    """Store mock storionX metadata entities in memory."""

    def _key(self, item: Metadata) -> str:
        """Return the metadata identifier used as the storage key."""

        return "|".join((item.author, item.department, item.retention_policy))


__all__: list[str] = [
    "DocumentStorage",
    "FolderStorage",
    "MetadataStorage",
    "UploadSessionStorage",
    "WorkspaceStorage",
]
