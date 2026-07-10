"""Enterprise Vault builder for the mock Enterprise Vault subsystem.

This module defines the top-level builder responsible for composing mock
Enterprise Vault structures in a layered and extensible fashion.
"""

from __future__ import annotations

from collections.abc import Sequence

from mock_ev.entities import Archive, VaultStore


class EnterpriseVaultBuilder:
    """Build complete mock Enterprise Vault vault stores."""

    def build_vault_store(
        self,
        *,
        name: str,
        archives: Sequence[Archive] | None = None,
    ) -> VaultStore:
        """Construct a vault store from already-built archive objects."""

        return VaultStore(name=name, archives=list(archives or []))


__all__: list[str] = ["EnterpriseVaultBuilder"]
