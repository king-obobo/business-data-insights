# GitHub Data Ingestion Pipeline

A resilient Python ingestion service that fetches public GitHub repository metadata
for multiple organizations, validates each record against strict schema and business
rules, routes invalid records to a quarantine table, persists trustworthy data to
PostgreSQL, and exposes live data-quality metrics and operational status through a
FastAPI service layer.

## Organizations ingested

`stripe`, `shopify`, `microsoft` — chosen to give the quality report and
`pipeline_runs` metadata more than one batch to compare across.

## Architecture

```
main.py            CLI entrypoint: start_run() / process_run() / run_ingestion()
                    orchestrates client -> schema -> repository for one org

src/
  client.py         GitHubClient: auth, timeouts, Link-header pagination,
                     exponential backoff, rate-limit handling, raw page capture
  schema.py          Repo (Pydantic): field + cross-field validation
  repository.py      All Postgres access (parameterized SQL, UPSERT, quarantine,
                      pipeline_runs, pagination) — no ORM
  quality.py          5-dimension data quality engine, computed live from the DB
  api.py               FastAPI service layer (5 endpoints, background ingestion)
  exceptions.py        GitHubApiError / ResourceNotFound
  logger.py             Rotating file + console logging

schema.sql            pipeline_runs, github_repos, github_repos_quarantine
                       (explicit constraints, FKs, one-running-run-per-org index)

tests/
  test_client.py       pagination, retries, backoff, rate-limit, malformed JSON
  test_schema.py        validators: valid/missing/wrong-type/negative/cross-field
  test_repository.py     upsert, quarantine, FK enforcement, pipeline_runs counts
  test_api.py             all 5 endpoints, success + error paths, mocked data layer
  test_quality.py         quality-dimension math (pure) + DB-backed accuracy checks
conftest.py               shared fixtures (fake token, temp raw dir, DB connection,
                           no real time.sleep during tests)
```

**Data flow for one ingestion run:**

1. `POST /ingest/{org}` (or the CLI) calls `start_run(org)`, which inserts a
   `pipeline_runs` row with `status='running'`. A unique index on `(org)` where
   `status='running'` means a second concurrent run for the same org fails here —
   this is what the API translates into an HTTP `409`.
2. `process_run(run_id, org)` runs (in the background for the API, inline for the
   CLI): `GitHubClient.fetch_org_repos()` pages through `/orgs/{org}/repos`,
   writing each raw page to `data/raw/{org}/{run_timestamp}_page{N}.json` before
   any parsing happens.
3. Each raw record is validated against the `Repo` model. Valid records are
   `UPSERT`ed into `github_repos`; invalid records are hashed and inserted into
   `github_repos_quarantine` with the failed field and specific error message
   (deduplicated on `(org, payload_hash)` so re-running doesn't duplicate the
   same bad record).
4. `finish_run()` updates the `pipeline_runs` row with final counts and status.

## Setup

**Requirements:** Python 3.11+, a reachable PostgreSQL instance, [uv](https://docs.astral.sh/uv/).

```bash
# install dependencies (reads pyproject.toml / uv.lock)
uv sync
```

**Environment variables** — create a `.env` file in the project root:

```
GITHUB_TOKEN=your_github_personal_access_token
DATABASE_URL=postgresql://user:password@localhost:5432/github_ingestion
```

- `GITHUB_TOKEN` is optional — if absent, the client logs a warning and runs
  unauthenticated (capped at 60 requests/hour by GitHub, which is not enough
  quota to ingest all three configured orgs in one run).
- Neither value is ever exposed in API responses or error messages.

**Apply the schema** (safe to re-run; uses `CREATE TABLE IF NOT EXISTS`):

```bash
psql -U <user> -d <database> -f schema.sql
```

## Running the pipeline (CLI)

```bash
uv run main.py
```

Fetches and ingests all configured orgs sequentially, logging progress to the
console and to `logs/pipeline.log`.

## Running the API

```bash
uv run uvicorn src.api:app --reload
```

Interactive docs (auto-generated from the code) at `http://127.0.0.1:8000/docs`.

### Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/ingest/{org}` | Starts an ingestion run in the background, returns `run_id` immediately. `409` if a run is already in progress for that org. |
| `GET` | `/runs/{run_id}` | Status and metadata for one run. `404` if unknown, `422` if `run_id` isn't a valid UUID. |
| `GET` | `/runs` | Recent runs, most recent first. |
| `GET` | `/quality-report/{org}` | Live 5-dimension quality scores for the org's latest completed run. `404` if none exists. |
| `GET` | `/quarantine/{org}?page=&page_size=` | Paginated quarantined records with their failed field and error message. |

### Example

```bash
curl -X POST http://127.0.0.1:8000/ingest/stripe
curl http://127.0.0.1:8000/runs/<run_id>
curl http://127.0.0.1:8000/quality-report/stripe
curl "http://127.0.0.1:8000/quarantine/stripe?page=1&page_size=20"
```

## Data quality dimensions

Computed live in `src/quality.py` from `pipeline_runs`, `github_repos`, and
`github_repos_quarantine` combined (not from a report file) — the quarantine
table's raw payloads are merged back with the clean table so dimensions like
completeness and consistency measure the *entire* fetched batch, not just the
records that already passed validation.

| Dimension | How it's measured |
|---|---|
| Completeness | Non-null rate per required field; `description` reported separately |
| Validity | `records_valid / records_fetched` from `pipeline_runs` |
| Uniqueness | Duplicate `id` count across the combined batch |
| Consistency | Share of records where `pushed_at >= created_at` |
| Accuracy | Random sample of stored repos re-fetched live from GitHub and compared field-by-field |

## Testing

```bash
uv run pytest --cov=src --cov-report=term-missing
```

- `test_client.py` / `test_schema.py` — pure unit tests, no database or network
  required (HTTP is mocked, `time.sleep` is patched out via the `sleeps` fixture).
- `test_repository.py` / `test_quality.py` (DB-backed cases) — run against a real
  `DATABASE_URL`; every test's writes happen inside a transaction that is rolled
  back on teardown, so nothing persists into real data.
- `test_api.py` — uses FastAPI's `TestClient` with the data layer mocked, so it
  tests routing, status codes, and input validation in isolation from the database.

Target: 80%+ line coverage on `src/`, with each listed failure path exercised
directly rather than only happy-path reads.

## Design decisions worth knowing (not spelled out by the assessment)

- **No ORM** — all queries are plain parameterized SQL via `psycopg` (v3).
- **Quarantine dedup key** is a SHA-256 hash of the full raw payload (not just the
  repo `id`), so a record that was invalid and comes back identically invalid on a
  later run is skipped, while a record whose payload actually changed is inserted
  as a new quarantine row.
- **One connection/transaction per ingestion run** — a hard crash mid-run rolls
  back the whole run, including its `pipeline_runs` row, rather than leaving a
  stuck `'running'` row behind.
- **`clock_timestamp()`, not `now()`**, for `started_at`/`finished_at` — `now()`
  is fixed for the whole transaction in Postgres, which would otherwise make
  every run's `finished_at` equal to its `started_at` regardless of real duration.
- **`POST /ingest/{org}`** uses FastAPI `BackgroundTasks`, which runs after the
  response is sent but within the same process — sufficient for this project's
  scope; a production system under heavier load would use a real task queue.



pytest --cov=src --cov-report=term-missing

http://127.0.0.1:8000/docs#/