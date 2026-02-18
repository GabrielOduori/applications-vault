import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.config import settings
from app.services.vault_service import vault_service, VaultService


def _set_sqlite_pragmas(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


@pytest.fixture
def tmp_vault(tmp_path):
    vault_path = tmp_path / "TestVault"
    vault_path.mkdir()
    return vault_path


@pytest.fixture
def test_db(tmp_vault):
    db_path = tmp_vault / "db.sqlite"
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )
    event.listen(engine, "connect", _set_sqlite_pragmas)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    from app.database import init_db
    init_db(db_path)

    def override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestSession
    app.dependency_overrides.clear()


@pytest.fixture
def fresh_vault_service():
    """Reset vault service state for each test."""
    original = vault_service.__dict__.copy()
    vault_service._active_tokens = {}
    vault_service._failed_attempts = 0
    vault_service._last_failed_at = 0
    yield vault_service
    vault_service.__dict__.update(original)


@pytest.fixture
def client(tmp_vault, test_db, fresh_vault_service):
    original_vault_path = settings.vault_path
    settings.vault_path = tmp_vault
    c = TestClient(app)
    yield c
    settings.vault_path = original_vault_path
