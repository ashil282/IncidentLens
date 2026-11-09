import pytest
from fastapi.testclient import TestClient

from incidentlens.config import get_settings
from incidentlens.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("INCIDENTLENS_DATABASE_PATH", str(tmp_path / "test.db"))
    get_settings.cache_clear()
    with TestClient(app) as test_client:
        yield test_client
    get_settings.cache_clear()
