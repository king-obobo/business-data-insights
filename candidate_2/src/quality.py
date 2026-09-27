# src/quality.py
from datetime import datetime
from .exceptions import GitHubApiError
from .logger import setup_logger

logger = setup_logger(__name__)

REQUIRED_FIELDS = [
    "id", "name", "full_name", "private", "html_url",
    "stargazers_count", "forks_count", "open_issues_count",
    "archived", "created_at", "updated_at", "pushed_at",
]


def _latest_run(conn, org):
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT run_id, records_fetched, records_valid, records_quarantined
            FROM pipeline_runs
            WHERE org = %s AND status = 'completed'
            ORDER BY started_at DESC
            LIMIT 1
            """,
            (org,),
        )
        row = cur.fetchone()
    if row is None:
        return None
    return {
        "run_id": row[0],
        "records_fetched": row[1],
        "records_valid": row[2],
        "records_quarantined": row[3],
    }


def _fetch_combined_records(conn, run_id):
    """Every record GitHub returned this run: valid rows + quarantined raw payloads."""
    records = []
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, name, full_name, private, html_url, description,stargazers_count, forks_count, open_issues_count, archived,created_at, updated_at, pushed_at
            FROM github_repos WHERE run_id = %s
            """,
            (run_id,),
        )
        columns = [desc[0] for desc in cur.description]
        for row in cur.fetchall():
            records.append(dict(zip(columns, row)))

        cur.execute(
            "SELECT raw_payload FROM github_repos_quarantine WHERE run_id = %s",
            (run_id,),
        )
        for (raw_payload,) in cur.fetchall():
            records.append(raw_payload)

    return records


def _parse_dt(value):
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def _completeness(records):
    total = len(records)
    if total == 0:
        return {"per_field": {}, "description_rate": None}

    per_field = {
        field: round(sum(1 for r in records if r.get(field) is not None) / total, 4)
        for field in REQUIRED_FIELDS
    }
    description_rate = round(
        sum(1 for r in records if r.get("description") is not None) / total, 4
    )
    return {"per_field": per_field, "description_rate": description_rate}


def _validity(run_stats):
    total = run_stats["records_fetched"]
    return round(run_stats["records_valid"] / total, 4) if total else None


def _uniqueness(records):
    ids = [r.get("id") for r in records if r.get("id") is not None]
    return len(ids) - len(set(ids))


def _consistency(records):
    total = consistent = 0
    for r in records:
        created = _parse_dt(r.get("created_at"))
        pushed = _parse_dt(r.get("pushed_at"))
        if created is None or pushed is None:
            continue
        total += 1
        if pushed >= created:
            consistent += 1
    return round(consistent / total, 4) if total else None


def _accuracy(conn, client, org, run_id, sample_size=5):
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT name, stargazers_count, forks_count, open_issues_count, archived
            FROM github_repos
            WHERE run_id = %s
            ORDER BY random()
            LIMIT %s
            """,
            (run_id, sample_size),
        )
        sample = cur.fetchall()

    if not sample:
        return None

    matches = checked = 0
    for name, stars, forks, open_issues, archived in sample:
        try:
            live = client.get_repo(org, name)
        except GitHubApiError as exc:
            logger.warning(f"Accuracy check skipped {org}/{name}: {exc}")
            continue
        checked += 1
        if (
            live.get("stargazers_count") == stars
            and live.get("forks_count") == forks
            and live.get("open_issues_count") == open_issues
            and live.get("archived") == archived
        ):
            matches += 1

    return round(matches / checked, 4) if checked else None


def compute_quality_report(conn, client, org):
    """Compute all 5 quality dimensions for an org's latest completed run."""
    run_stats = _latest_run(conn, org)
    if run_stats is None:
        return None

    records = _fetch_combined_records(conn, run_stats["run_id"])

    return {
        "org": org,
        "run_id": str(run_stats["run_id"]),
        "records_fetched": run_stats["records_fetched"],
        "completeness": _completeness(records),
        "validity": _validity(run_stats),
        "uniqueness": {"duplicate_id_count": _uniqueness(records)},
        "consistency": _consistency(records),
        "accuracy": _accuracy(conn, client, org, run_stats["run_id"]),
    }