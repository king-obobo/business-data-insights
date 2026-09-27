import uuid
import psycopg
import pytest

from src.repository import (
    upsert_repo, insert_quarantine, create_run, finish_run, get_run,
)


def test_upsert_repo_inserts_new_record(db_conn, run_id, valid_repo_data):
    upsert_repo(db_conn, valid_repo_data, org="stripe", run_id=run_id)

    with db_conn.cursor() as cur:
        cur.execute("SELECT name FROM github_repos WHERE id = %s", (valid_repo_data["id"],))
        row = cur.fetchone()

    assert row is not None
    assert row[0] == "stripe-node"


def test_upsert_repo_updates_on_conflict(db_conn, run_id, valid_repo_data):
    upsert_repo(db_conn, valid_repo_data, org="stripe", run_id=run_id)

    changed = {**valid_repo_data, "stargazers_count": 99999}
    upsert_repo(db_conn, changed, org="stripe", run_id=run_id)

    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT count(*), max(stargazers_count) FROM github_repos WHERE id = %s",
            (valid_repo_data["id"],),
        )
        count, stars = cur.fetchone()

    assert count == 1  # no duplicate row
    assert stars == 99999  # updated, not ignored


def test_quarantine_persists_raw_payload_and_error_metadata(db_conn, run_id):
    raw = {"id": 999, "name": "", "note": "bad record"}

    insert_quarantine(db_conn, run_id, "stripe", raw, "name", "must not be empty")

    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT raw_payload, failed_field, error_message, org "
            "FROM github_repos_quarantine WHERE run_id = %s",
            (run_id,),
        )
        payload, failed_field, error_message, org = cur.fetchone()

    assert payload == raw
    assert failed_field == "name"
    assert error_message == "must not be empty"
    assert org == "stripe"


def test_upsert_repo_rejects_unknown_run_id(db_conn, valid_repo_data):
    """A repo referencing a run_id that doesn't exist must be rejected by the FK, not silently stored."""
    fake_run_id = uuid.uuid4()

    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        upsert_repo(db_conn, valid_repo_data, org="stripe", run_id=fake_run_id)


def test_pipeline_run_reflects_counts(db_conn):
    rid = uuid.uuid4()
    create_run(db_conn, rid, "stripe")
    finish_run(
        db_conn, rid,
        records_fetched=10, records_valid=9, records_quarantined=1,
        status="completed",
    )

    run = get_run(db_conn, rid)

    assert run["status"] == "completed" # type: ignore
    assert run["records_fetched"] == 10 # type: ignore
    assert run["records_valid"] == 9 # type: ignore
    assert run["records_quarantined"] == 1 # type: ignore