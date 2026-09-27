import pytest
import time
import uuid
from src.repository import get_connection, create_run
from src.client import GitHubClient
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

from src.api import app


@pytest.fixture
def valid_repo_data():
    return {
        "id": 2471804,
        "name": "stripe-node",
        "full_name": "stripe/stripe-node",
        "private": False,
        "html_url": "https://github.com/stripe/stripe-node",
        "description": "Node.js library for the Stripe API.",
        "stargazers_count": 4507,
        "forks_count": 935,
        "open_issues_count": 44,
        "archived": False,
        "created_at": "2011-09-28T00:28:33Z",
        "updated_at": "2026-09-17T20:03:19Z",
        "pushed_at": "2026-09-18T13:49:09Z",
    }


@pytest.fixture
def sleeps(monkeypatch):
    """Replace time.sleep; the list records every delay the client requested."""
    recorded = []
    monkeypatch.setattr(time, "sleep", recorded.append)
    return recorded


@pytest.fixture
def client(tmp_path, sleeps):
    """Client with a fake token, raw pages going to a temp folder, no real sleeping."""
    return GitHubClient(token="test-token", max_retries=3, raw_dir=str(tmp_path))


@pytest.fixture
def db_conn():
    """Real Postgres connection; rolled back (never committed) after each test."""
    conn = get_connection()
    yield conn
    conn.rollback()
    conn.close()


@pytest.fixture
def run_id(db_conn):
    """A pipeline_runs row to satisfy FK constraints on github_repos / quarantine."""
    rid = uuid.uuid4()
    create_run(db_conn, rid, "stripe")
    return rid


@pytest.fixture
def api_client():
    return TestClient(app)


@pytest.fixture
def fake_conn(monkeypatch):
    """Patch get_connection so endpoints don't need a real DB connection.
    Only needed for endpoints that call `with get_connection() as conn:`
    directly (quality-report, runs, quarantine) — not /ingest, which
    delegates connection handling to start_run/process_run in main.py."""
    conn = MagicMock()
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=conn)
    cm.__exit__ = MagicMock(return_value=False)
    monkeypatch.setattr("src.api.get_connection", lambda: cm)
    return conn