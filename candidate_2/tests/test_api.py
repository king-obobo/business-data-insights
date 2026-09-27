import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import psycopg



# --- GET /quality-report/{org} ---

def test_quality_report_returns_scores(api_client, fake_conn, monkeypatch):
    fake_report = {
        "org": "shopify",
        "run_id": "499078c0-af36-48a7-a377-ae313dc64b1a",
        "records_fetched": 1229,
        "completeness": {"per_field": {}, "description_rate": 0.81},
        "validity": 0.9463,
        "uniqueness": {"duplicate_id_count": 0},
        "consistency": 0.9463,
        "accuracy": 1.0,
    }
    monkeypatch.setattr("src.api.compute_quality_report", lambda conn, client, org: fake_report)

    response = api_client.get("/quality-report/shopify")

    assert response.status_code == 200
    assert response.json() == fake_report


def test_quality_report_404_when_no_completed_run(api_client, fake_conn, monkeypatch):
    monkeypatch.setattr("src.api.compute_quality_report", lambda conn, client, org: None)

    response = api_client.get("/quality-report/not-a-real-org")

    assert response.status_code == 404
    assert "not-a-real-org" in response.json()["detail"]


# --- GET /runs/{run_id} and GET /runs ---

def test_read_run_returns_metadata_for_known_run(api_client, fake_conn, monkeypatch):
    rid = uuid.uuid4()
    fake_run = {
        "run_id": rid,
        "org": "stripe",
        "started_at": datetime.now(timezone.utc),
        "finished_at": datetime.now(timezone.utc),
        "records_fetched": 99,
        "records_valid": 99,
        "records_quarantined": 0,
        "status": "completed",
    }
    monkeypatch.setattr("src.api.get_run", lambda conn, run_id: fake_run)

    response = api_client.get(f"/runs/{rid}")

    assert response.status_code == 200
    body = response.json()
    assert body["run_id"] == str(rid)
    assert body["status"] == "completed"
    assert body["records_fetched"] == 99


def test_read_run_404_for_unknown_run(api_client, fake_conn, monkeypatch):
    monkeypatch.setattr("src.api.get_run", lambda conn, run_id: None)

    response = api_client.get(f"/runs/{uuid.uuid4()}")

    assert response.status_code == 404


def test_read_run_422_for_malformed_run_id(api_client):
    """No mocking needed: FastAPI rejects this before our code runs at all."""
    response = api_client.get("/runs/not-a-uuid")

    assert response.status_code == 422


def test_read_runs_lists_most_recent_first(api_client, fake_conn, monkeypatch):
    fake_runs = [
        {"run_id": uuid.uuid4(), "org": "microsoft", "status": "completed"},
        {"run_id": uuid.uuid4(), "org": "shopify", "status": "completed"},
    ]
    monkeypatch.setattr("src.api.list_runs", lambda conn: fake_runs)

    response = api_client.get("/runs")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    assert body[0]["org"] == "microsoft"


# --- POST /ingest/{org} ---

def test_ingest_returns_run_id_without_blocking(api_client, monkeypatch):
    fixed_run_id = uuid.uuid4()
    mock_start_run = MagicMock(return_value=fixed_run_id)
    mock_process_run = MagicMock()  # stands in for the real fetch/validate/persist work

    monkeypatch.setattr("src.api.start_run", mock_start_run)
    monkeypatch.setattr("src.api.process_run", mock_process_run)

    response = api_client.post("/ingest/stripe")

    assert response.status_code == 200
    body = response.json()
    assert body["run_id"] == str(fixed_run_id)
    assert body["org"] == "stripe"
    assert body["status"] == "running"

    # Proves the endpoint scheduled the real work rather than doing it inline —
    # start_run ran synchronously (we got a run_id back), and process_run was
    # handed to BackgroundTasks with the same run_id/org, not called and awaited
    # as part of building the response.
    mock_start_run.assert_called_once_with("stripe")
    mock_process_run.assert_called_once_with(fixed_run_id, "stripe")


def test_ingest_409_when_run_already_in_progress(api_client, monkeypatch):
    def raise_conflict(org):
        raise psycopg.errors.UniqueViolation("duplicate key value violates unique constraint")

    monkeypatch.setattr("src.api.start_run", raise_conflict)

    response = api_client.post("/ingest/microsoft")

    assert response.status_code == 409
    assert "microsoft" in response.json()["detail"]


# --- GET /quarantine/{org} ---

def test_quarantine_returns_paginated_results(api_client, fake_conn, monkeypatch):
    fake_page = {
        "records": [
            {"quarantine_id": 1, "org": "shopify", "failed_field": "pushed_at,created_at",
            "error_message": "Value error, pushed_at must not be before created_at"}
        ],
        "page": 1,
        "page_size": 20,
        "total": 66,
    }
    monkeypatch.setattr(
        "src.api.list_quarantine",
        lambda conn, org, page, page_size: fake_page,
    )

    response = api_client.get("/quarantine/shopify")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 66
    assert body["page"] == 1
    assert len(body["records"]) == 1


def test_quarantine_422_for_non_integer_page(api_client):
    response = api_client.get("/quarantine/shopify?page=abc")

    assert response.status_code == 422