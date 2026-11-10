import pytest
from fastapi.testclient import TestClient

from incidentlens.config import get_settings
from incidentlens.database import Database
from incidentlens.main import app
from incidentlens.models import Base


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.delenv("INCIDENTLENS_DATABASE_URL", raising=False)
    monkeypatch.setenv("INCIDENTLENS_DATABASE_PATH", str(tmp_path / "test.db"))
    get_settings.cache_clear()

    settings = get_settings()
    test_database = Database(settings)
    try:
        Base.metadata.create_all(test_database.engine)
    finally:
        test_database.dispose()

    with TestClient(app) as test_client:
        yield test_client

    get_settings.cache_clear()
