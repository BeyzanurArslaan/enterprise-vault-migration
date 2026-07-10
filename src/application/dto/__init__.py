"""Data transfer objects for the application layer.

These lightweight structures define the shape of inputs and outputs exchanged
between application flows and their callers.
"""

from __future__ import annotations

from application.dto.assessment_result import AssessmentResult
from application.dto.migration_request import MigrationRequest
from application.dto.migration_result import MigrationResult
from application.dto.upload_result import UploadResult

__all__: list[str] = [
    "AssessmentResult",
    "MigrationRequest",
    "MigrationResult",
    "UploadResult",
]
