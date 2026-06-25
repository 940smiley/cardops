from __future__ import annotations

import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
for extra in [ROOT / "apps/api", ROOT / "apps/worker", ROOT / "packages/schemas/python"]:
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    database_path = tmp_path / "cardops-test.db"
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.chdir(ROOT)
    monkeypatch.setenv("CARDOPS_DATABASE_URL", f"sqlite:///{database_path.as_posix()}")
    monkeypatch.setenv("CARDOPS_DATA_DIR", str(data_dir))
    monkeypatch.setenv("CARDOPS_DEMO_MODE", "false")
    monkeypatch.setenv("CARDOPS_CLOUD_AI_ENABLED", "false")
    monkeypatch.setenv("CARDOPS_LOCAL_ONLY_MODE", "true")
    monkeypatch.setenv("EBAY_CLIENT_ID", "")
    monkeypatch.setenv("EBAY_CLIENT_SECRET", "")
    monkeypatch.setenv("EBAY_RUNAME", "")
    monkeypatch.setenv("EBAY_REFRESH_TOKEN", "")

    from cardops_api.config import clear_settings_cache
    from cardops_api.database import configure_database, init_db
    from cardops_api.main import app

    clear_settings_cache()
    configure_database(f"sqlite:///{database_path.as_posix()}")
    init_db()

    with TestClient(app) as test_client:
        yield test_client
