import uuid
from datetime import datetime, timezone
from pydantic import ValidationError

from src.logger import setup_logger
from src.client import GitHubClient
from src.exceptions import GitHubApiError
from src.schema import Repo
from src.repository import (
    get_connection,
    create_run,
    finish_run,
    upsert_repo,
    insert_quarantine,
)

logger = setup_logger(__name__)


def start_run(org: str) -> uuid.UUID:
    """Create the pipeline_runs row. Raises psycopg.errors.UniqueViolation
    if this org already has a run in progress."""
    run_id = uuid.uuid4()
    with get_connection() as conn:
        create_run(conn, run_id, org)
    return run_id


def process_run(run_id: uuid.UUID, org: str) -> None:
    """Fetch, validate, and persist. Assumes start_run already ran for run_id."""
    client = GitHubClient()
    with get_connection() as conn:
        run_timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        try:
            raw_repos = client.fetch_org_repos(org, run_timestamp)
        except GitHubApiError as exc:
            logger.error(f"Ingestion failed for {org}: {exc}")
            finish_run(conn, run_id, records_fetched=0, records_valid=0,
            records_quarantined=0, status="failed")
            return

        valid_count = 0
        quarantined_count = 0

        for raw in raw_repos:
            try:
                repo = Repo.model_validate(raw)
            except ValidationError as exc:
                first_error = exc.errors()[0]
                loc = first_error["loc"]
                failed_field = ".".join(str(p) for p in loc) if loc else "pushed_at,created_at"
                insert_quarantine(conn, run_id, org, raw, failed_field, first_error["msg"])
                quarantined_count += 1
                continue

            upsert_repo(conn, repo.model_dump(), org=org, run_id=run_id)
            valid_count += 1

        finish_run(
            conn, run_id,
            records_fetched=len(raw_repos),
            records_valid=valid_count,
            records_quarantined=quarantined_count,
            status="completed",
        )

    logger.info(f"Run {run_id} for {org}: {valid_count} valid, {quarantined_count} quarantined")


def run_ingestion(org: str) -> uuid.UUID:
    """CLI convenience: create + process synchronously, in one call."""
    run_id = start_run(org)
    process_run(run_id, org)
    return run_id


def main() -> None:
    orgs = ["stripe", "shopify", "microsoft"]
    for org in orgs:
        run_ingestion(org)


if __name__ == "__main__":
    main()