import os
import psycopg
import hashlib
import json
from dotenv import load_dotenv
from .logger import setup_logger

load_dotenv()
logger = setup_logger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")


def get_connection() -> psycopg.Connection:
    """Open a new connection using DATABASE_URL from the environment."""
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL environment variable is not set")
    return psycopg.connect(DATABASE_URL)


def create_run(conn: psycopg.Connection, run_id, org: str) -> None:
    """Insert a new pipeline_runs row with status='running'."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO pipeline_runs (run_id, org, status)
            VALUES (%s, %s, 'running')
            """,
            (run_id, org),
        )


def finish_run(
    conn: psycopg.Connection,
    run_id,
    records_fetched: int,
    records_valid: int,
    records_quarantined: int,
    status: str,
) -> None:
    """Update a pipeline_runs row once ingestion has finished."""
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE pipeline_runs
            SET finished_at = clock_timestamp(),
                records_fetched = %s,
                records_valid = %s,
                records_quarantined = %s,
                status = %s
            WHERE run_id = %s
            """,
            (records_fetched, records_valid, records_quarantined, status, run_id),
        )


def upsert_repo(conn: psycopg.Connection, repo: dict, org: str, run_id) -> None:
    """Insert a validated repo, or update it if the id already exists."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO github_repos (
                id, name, full_name, private, html_url, description,
                stargazers_count, forks_count, open_issues_count, archived,
                created_at, updated_at, pushed_at, org, run_id
            )
            VALUES (
                %(id)s, %(name)s, %(full_name)s, %(private)s, %(html_url)s, %(description)s,
                %(stargazers_count)s, %(forks_count)s, %(open_issues_count)s, %(archived)s,
                %(created_at)s, %(updated_at)s, %(pushed_at)s, %(org)s, %(run_id)s
            )
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                full_name = EXCLUDED.full_name,
                private = EXCLUDED.private,
                html_url = EXCLUDED.html_url,
                description = EXCLUDED.description,
                stargazers_count = EXCLUDED.stargazers_count,
                forks_count = EXCLUDED.forks_count,
                open_issues_count = EXCLUDED.open_issues_count,
                archived = EXCLUDED.archived,
                created_at = EXCLUDED.created_at,
                updated_at = EXCLUDED.updated_at,
                pushed_at = EXCLUDED.pushed_at,
                org = EXCLUDED.org,
                run_id = EXCLUDED.run_id,
                ingested_at = now()
            """,
            {**repo, "org": org, "run_id": run_id},
        )


def insert_quarantine(
    conn: psycopg.Connection,
    run_id,
    org: str,
    raw_payload: dict,
    failed_field: str,
    error_message: str,
) -> None:
    """Store an invalid record. Same (org, payload) pair is skipped on repeat runs."""
    payload_json = json.dumps(raw_payload, sort_keys=True)
    payload_hash = hashlib.sha256(payload_json.encode()).hexdigest()

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO github_repos_quarantine (
                run_id, org, raw_payload, payload_hash, failed_field, error_message
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (org, payload_hash) DO NOTHING
            """,
            (run_id, org, payload_json, payload_hash, failed_field, error_message),
        )
        
def get_run(conn, run_id):
    """Fetch one pipeline_runs row by run_id, or None if it doesn't exist."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT run_id, org, started_at, finished_at,
                records_fetched, records_valid, records_quarantined, status
            FROM pipeline_runs
            WHERE run_id = %s
            """,
            (run_id,),
        )
        row = cur.fetchone()

    if row is None:
        return None

    columns = ["run_id", "org", "started_at", "finished_at","records_fetched", "records_valid", "records_quarantined", "status"]
    return dict(zip(columns, row))


def list_runs(conn, limit=20):
    """Most recent pipeline_runs first."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT run_id, org, started_at, finished_at,
                records_fetched, records_valid, records_quarantined, status
            FROM pipeline_runs
            ORDER BY started_at DESC
            LIMIT %s
            """,
            (limit,),
        )
        columns = [desc[0] for desc in cur.description]
        return [dict(zip(columns, row)) for row in cur.fetchall()]
    

def list_quarantine(conn, org: str, page: int = 1, page_size: int = 20):
    """Paginated quarantine records for an org, most recent first."""
    offset = (page - 1) * page_size

    with conn.cursor() as cur:
        cur.execute(
            "SELECT count(*) FROM github_repos_quarantine WHERE org = %s",
            (org,),
        )
        total = cur.fetchone()[0]

        cur.execute(
            """
            SELECT quarantine_id, org, failed_field, error_message, quarantined_at
            FROM github_repos_quarantine
            WHERE org = %s
            ORDER BY quarantined_at DESC
            LIMIT %s OFFSET %s
            """,
            (org, page_size, offset),
        )
        columns = [desc[0] for desc in cur.description]
        records = [dict(zip(columns, row)) for row in cur.fetchall()]

    return {"records": records, "page": page, "page_size": page_size, "total": total}