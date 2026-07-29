"""Shared pytest fixtures.

Each test gets a fresh ephemeral data dir (db + secrets + artifacts), a
configured AppConfig, an initialized engine, and a FastAPI TestClient. No
real network or SSH is used.
"""
from __future__ import annotations

import importlib
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def tmp_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    data = tmp_path / "data"
    data.mkdir()
    (data / "secrets").mkdir()
    (data / "artifacts").mkdir()
    monkeypatch.setenv("DIRTYLAB_DATA_DIR", str(data))
    # Reset the cached config.
    for mod in (
        "app.core.config",
        "app.db.base",
        "app.main",
    ):
        if mod in sys.modules:
            importlib.reload(sys.modules[mod])
    return data


@pytest.fixture
def app(tmp_data_dir: Path):
    from app.core.config import AppConfig
    from app.main import create_app

    config = AppConfig.load(tmp_data_dir)
    application = create_app(config)
    return application


@pytest.fixture
def client(app) -> Iterator[TestClient]:
    # Use TestClient as a context manager so lifespan startup runs and the
    # database engine is initialized.
    with TestClient(app) as c:
        yield c


@pytest.fixture
def db_session(tmp_data_dir: Path):
    from app.core.config import AppConfig
    from app.db.base import init_engine, session_scope
    from app.db.bootstrap import create_schema, ensure_seed_data

    cfg = AppConfig.load(tmp_data_dir)
    engine = init_engine(cfg)
    create_schema(engine)
    with session_scope() as s:
        ensure_seed_data(s)
        yield s
