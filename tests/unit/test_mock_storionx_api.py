"""Unit tests for the mock storionX API façade layer."""

from __future__ import annotations

from mock_storionx.api import HealthAPI, MetadataAPI, SearchAPI, UploadAPI


def test_api_classes_can_be_instantiated() -> None:
    """The API façade classes should be directly instantiable."""

    assert UploadAPI() is not None
    assert SearchAPI() is not None
    assert MetadataAPI() is not None
    assert HealthAPI() is not None


def test_api_public_methods_exist() -> None:
    """The API façade classes should expose the expected public methods."""

    upload_api = UploadAPI()
    search_api = SearchAPI()
    metadata_api = MetadataAPI()
    health_api = HealthAPI()

    assert callable(upload_api.upload_document)
    assert callable(upload_api.finalize_upload)
    assert callable(search_api.search_documents)
    assert callable(search_api.search_metadata)
    assert callable(metadata_api.create_metadata)
    assert callable(metadata_api.get_metadata)
    assert callable(metadata_api.update_metadata)
    assert callable(metadata_api.delete_metadata)
    assert callable(metadata_api.list_metadata)
    assert callable(health_api.health_check)


def test_health_api_returns_placeholder_response() -> None:
    """The health API should return the expected placeholder response."""

    assert HealthAPI().health_check() == {"status": "ok"}
