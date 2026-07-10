"""Service package for the mock Enterprise Vault subsystem.

This package reserves the services that would expose discovery, streaming, and
assessment capabilities over the mocked source data.
"""

from __future__ import annotations

__all__: list[str] = [
    "discovery_service",
    "streaming_service",
    "assessment_service",
]
