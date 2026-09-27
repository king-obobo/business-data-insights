-- GitHub ingestion pipeline schema.
-- Safe to run more than once (IF NOT EXISTS).
-- pipeline_runs comes first because the other two tables reference it.

-- pipeline_runs: operational log for each ingestion run
CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id                UUID PRIMARY KEY,
    org                   TEXT NOT NULL,
    started_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at           TIMESTAMPTZ,
    records_fetched       INTEGER NOT NULL DEFAULT 0 CHECK (records_fetched >= 0),
    records_valid         INTEGER NOT NULL DEFAULT 0 CHECK (records_valid >= 0),
    records_quarantined   INTEGER NOT NULL DEFAULT 0 CHECK (records_quarantined >= 0),
    status                TEXT NOT NULL DEFAULT 'running'
                            CHECK (status IN ('running', 'completed', 'failed'))
);

-- At most one 'running' run per org: a second insert violates this index,
-- which is how the API detects "run already in progress" (HTTP 409).
CREATE UNIQUE INDEX IF NOT EXISTS one_running_run_per_org
    ON pipeline_runs (org) WHERE status = 'running';

-- github_repos: clean, validated records only
CREATE TABLE IF NOT EXISTS github_repos (
    id                  BIGINT PRIMARY KEY,
    name                TEXT NOT NULL CHECK (length(trim(name)) > 0),
    full_name           TEXT NOT NULL CHECK (length(trim(full_name)) > 0),
    private             BOOLEAN NOT NULL,
    html_url            TEXT NOT NULL,
    description         TEXT,
    stargazers_count    INTEGER NOT NULL CHECK (stargazers_count >= 0),
    forks_count         INTEGER NOT NULL CHECK (forks_count >= 0),
    open_issues_count   INTEGER NOT NULL CHECK (open_issues_count >= 0),
    archived            BOOLEAN NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL,
    updated_at          TIMESTAMPTZ NOT NULL,
    pushed_at           TIMESTAMPTZ NOT NULL,
    org                 TEXT NOT NULL,
    run_id              UUID NOT NULL REFERENCES pipeline_runs (run_id),
    ingested_at         TIMESTAMPTZ NOT NULL DEFAULT now(),

    CHECK (pushed_at >= created_at)
);

-- github_repos_quarantine: invalid records, isolated with diagnostic metadata
CREATE TABLE IF NOT EXISTS github_repos_quarantine (
    quarantine_id   BIGSERIAL PRIMARY KEY,
    run_id          UUID NOT NULL REFERENCES pipeline_runs (run_id),
    org             TEXT NOT NULL,
    raw_payload     JSONB NOT NULL,
    payload_hash    TEXT NOT NULL,
    failed_field    TEXT NOT NULL,
    error_message   TEXT NOT NULL,
    quarantined_at  TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (org, payload_hash)
);

ALTER TABLE pipeline_runs ALTER COLUMN started_at SET DEFAULT clock_timestamp();