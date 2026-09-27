import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

from src.repository import upsert_repo, insert_quarantine, finish_run
from src.quality import (
    _completeness, _uniqueness, _consistency, _validity, _accuracy, compute_quality_report,
)


def _repo(overrides=None):
    base = {
        "id": 1, "name": "repo-a", "full_name": "org/repo-a", "private": False,
        "html_url": "https://github.com/org/repo-a", "description": "desc",
        "stargazers_count": 10, "forks_count": 2, "open_issues_count": 1,
        "archived": False,
        "created_at": datetime(2020, 1, 1, tzinfo=timezone.utc),
        "updated_at": datetime(2021, 1, 1, tzinfo=timezone.utc),
        "pushed_at": datetime(2021, 1, 1, tzinfo=timezone.utc),
    }
    if overrides:
        base.update(overrides)
    return base


# --- Pure functions: synthetic data, no DB ---

def test_completeness_all_present():
    result = _completeness([_repo(), _repo({"id": 2})])
    assert result["per_field"]["id"] == 1.0
    assert result["description_rate"] == 1.0


def test_completeness_handles_missing_description():
    result = _completeness([_repo(), _repo({"id": 2, "description": None})])
    assert result["description_rate"] == 0.5


def test_completeness_empty_input():
    assert _completeness([]) == {"per_field": {}, "description_rate": None}


def test_uniqueness_counts_duplicates():
    assert _uniqueness([_repo({"id": 1}), _repo({"id": 1}), _repo({"id": 2})]) == 1


def test_uniqueness_zero_when_unique():
    assert _uniqueness([_repo({"id": 1}), _repo({"id": 2})]) == 0


def test_consistency_flags_pushed_before_created():
    bad = _repo({
        "id": 1,
        "created_at": datetime(2022, 1, 1, tzinfo=timezone.utc),
        "pushed_at": datetime(2021, 1, 1, tzinfo=timezone.utc),
    })
    good = _repo({"id": 2})
    assert _consistency([bad, good]) == 0.5


def test_consistency_all_pass():
    assert _consistency([_repo({"id": 1}), _repo({"id": 2})]) == 1.0


def test_validity_from_run_stats():
    assert _validity({"records_fetched": 10, "records_valid": 9}) == 0.9


def test_validity_none_when_nothing_fetched():
    assert _validity({"records_fetched": 0, "records_valid": 0}) is None


# --- Real DB + fake GitHub client (no network calls) ---

def test_accuracy_matches_live_data(db_conn, run_id, valid_repo_data):
    upsert_repo(db_conn, valid_repo_data, org="stripe", run_id=run_id)

    fake_client = MagicMock()
    fake_client.get_repo.return_value = {
        "stargazers_count": valid_repo_data["stargazers_count"],
        "forks_count": valid_repo_data["forks_count"],
        "open_issues_count": valid_repo_data["open_issues_count"],
        "archived": valid_repo_data["archived"],
    }

    result = _accuracy(db_conn, fake_client, "stripe", run_id, sample_size=5)

    assert result == 1.0
    fake_client.get_repo.assert_called_once_with("stripe", valid_repo_data["name"])


def test_accuracy_none_when_no_repos_for_run(db_conn, run_id):
    fake_client = MagicMock()
    assert _accuracy(db_conn, fake_client, "stripe", run_id, sample_size=5) is None
    fake_client.get_repo.assert_not_called()


def test_compute_quality_report_none_without_completed_run(db_conn):
    fake_client = MagicMock()
    assert compute_quality_report(db_conn, fake_client, "org-with-no-runs") is None


def test_compute_quality_report_full_shape(db_conn, run_id, valid_repo_data):
    upsert_repo(db_conn, valid_repo_data, org="stripe", run_id=run_id)
    insert_quarantine(
        db_conn, run_id, "stripe",
        raw_payload={"id": 999, "name": ""},
        failed_field="name",
        error_message="must not be empty",
    )
    finish_run(db_conn, run_id, records_fetched=2, records_valid=1,
            records_quarantined=1, status="completed")

    fake_client = MagicMock()
    fake_client.get_repo.return_value = {
        "stargazers_count": valid_repo_data["stargazers_count"],
        "forks_count": valid_repo_data["forks_count"],
        "open_issues_count": valid_repo_data["open_issues_count"],
        "archived": valid_repo_data["archived"],
    }

    report = compute_quality_report(db_conn, fake_client, "stripe")

    assert report["org"] == "stripe" # type: ignore
    assert report["records_fetched"] == 2 # type: ignore
    assert report["validity"] == 0.5 # type: ignore
    assert report["uniqueness"]["duplicate_id_count"] == 0 # type: ignore
    assert report["accuracy"] == 1.0 # type: ignore