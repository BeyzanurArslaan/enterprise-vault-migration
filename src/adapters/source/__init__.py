"""Source adapters package for the migration platform.

This package groups adapter implementations that expose deterministic mock
Enterprise Vault sources through the source-port boundary.
"""

from __future__ import annotations

from .mock_enterprise_vault_source_adapter import MockEnterpriseVaultSourceAdapter

__all__: list[str] = ["MockEnterpriseVaultSourceAdapter"]
