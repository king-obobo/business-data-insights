# GitHub Data Ingestion Pipeline

A resilient Python data ingestion service that collects public GitHub repository metadata, validates each record against schema and business rules, quarantines invalid items, stores trustworthy data in PostgreSQL, and exposes operational and quality metrics through a FastAPI API.

## Overview

This project is designed to fetch repository data for multiple organizations, keep a reliable audit trail of ingestion runs, and surface data quality insights using a live reporting layer. It is built for reliability and observability rather than just raw extraction.

Key capabilities:

- fetches repository metadata from GitHub for selected organizations
- paginates through the GitHub API safely and handles rate limits
- validates each record using Pydantic models and custom checks
- quarantines invalid payloads with diagnostics rather than silently dropping them
- stores clean records and run metadata in PostgreSQL
- exposes endpoints for run status and quality tracking
- supports CLI-based and API-based ingestion flows

## Tech Stack

- Python 3.11+
- FastAPI
- Pydantic
- PostgreSQL
- psycopg (v3)
- requests
- pytest
- uv for dependency management

## Project Structure

```text
candidate_2/
├── main.py                  # CLI orchestration entrypoint
├── README.md                # project documentation
├── pyproject.toml           # Python dependencies and project metadata
├── docker-compose.yml       # Docker Compose stack for PostgreSQL + API service
├── Dockerfile               # container image for the FastAPI app
├── .env.example             # example environment configuration
├── data/
│   └── raw/                 # stored raw GitHub API responses
├── db/
│   └── schema.sql            # PostgreSQL schema and constraints
├── logs/                    # runtime logs
├── notebooks/
│   └── playground.ipynb     # exploratory notebook
├── scripts/                 # supporting scripts
├── src/
│   ├── api.py               # FastAPI endpoints and background job orchestration
│   ├── client.py            # GitHub API client with pagination and retry logic
│   ├── exceptions.py        # custom API-related exceptions
│   ├── logger.py            # logging setup
│   ├── quality.py           # data quality computations
│   ├── repository.py        # database access layer and SQL queries
│   ├── schema.py            # validated repository schema
│   └── __init__.py
├── tests/
│   ├── conftest.py
│   ├── test_api.py
│   ├── test_client.py
│   ├── test_quality.py
│   ├── test_repository.py
│   ├── test_schema.py
│   └── __init__.py
└── .env                     # local environment config (not committed)
```

## Data Flow

The ingestion lifecycle is structured around a run-based model:

1. A run is started for an organization using `start_run(org)`.
2. A `pipeline_runs` row is created and marked as `running`.
3. The GitHub client paginates over repository results and saves raw JSON responses.
4. Each record is validated using the `Repo` model.
5. Valid entries are upserted into the `github_repos` table.
6. Invalid entries are moved to the quarantine table with field-level error diagnostics.
7. The run is finalized with counts for fetched, valid, and quarantined records.

This design keeps the system auditable and helps isolate bad data without losing the original payload.

## Supported Organizations

The pipeline is set up to ingest the following organizations:

- `stripe`
- `shopify`
- `microsoft`

## Prerequisites

Before running the project, ensure you have:

- Python 3.11+
- PostgreSQL running and reachable
- a GitHub personal access token (recommended for higher rate limits)
- `uv` installed for dependency management

## Dockerized Setup

This project is fully dockerized and includes the following files in the project root:

- `Dockerfile` builds the Python application image and runs the FastAPI service.
- `docker-compose.yml` orchestrates the PostgreSQL database and the API container together.
- `.env.example` provides the environment variables required for Docker startup.

### Run the dockerized version

1. Copy the example environment file and configure your values:

```bash
cp .env.example .env
```

2. Build and start the services:

```bash
docker compose up --build
```

3. The application should be available at:

```text
http://localhost:8000/docs
```

4. To stop the containers:

```bash
docker compose down
```

5. To remove the database volume as well:

```bash
docker compose down -v
```

## Installation

Clone the project and install dependencies:

```bash
uv sync
```

## Environment Configuration

Create a `.env` file in the project root with the following values:

```env
GITHUB_TOKEN=your_github_personal_access_token
DATABASE_URL=postgresql://user:password@localhost:5432/github_ingestion
```

Notes:

- `GITHUB_TOKEN` is optional, but unauthenticated requests are rate-limited and may not be enough for full org runs.
- `DATABASE_URL` must point to a PostgreSQL database that already has the ingestion schema applied.

## Database Setup

Apply the schema to PostgreSQL:

```bash
psql -U <user> -d <database> -f db/schema.sql
```

The schema includes:

- `pipeline_runs`
- `github_repos`
- `github_repos_quarantine`

It is written to be safe to run more than once using `IF NOT EXISTS` checks and includes validation constraints to enforce data quality.

## Running the CLI Pipeline

Run the ingestion for all configured organizations:

```bash
uv run main.py
```

This will:

- start and finalize a run for each configured org
- persist repository data to PostgreSQL
- log progress to the console and the logs directory

## Running the FastAPI Service

Start the API:

```bash
uv run uvicorn src.api:app --reload
```

Then open the interactive docs at:

```text
http://127.0.0.1:8000/docs
```

### API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/ingest/{org}` | Start an ingestion run for an org in the background |
| `GET` | `/runs/{run_id}` | Fetch run metadata and status |
| `GET` | `/runs` | List recent runs |
| `GET` | `/quality-report/{org}` | Get the latest quality report for an org |
| `GET` | `/quarantine/{org}` | View paginated quarantine records |

Example requests:

```bash
curl -X POST http://127.0.0.1:8000/ingest/stripe
curl http://127.0.0.1:8000/runs/<run_id>
curl http://127.0.0.1:8000/quality-report/stripe
curl "http://127.0.0.1:8000/quarantine/stripe?page=1&page_size=20"
```

## Data Quality Metrics

The quality layer computes live scores from the database using the ingestion outcomes and stored repository data. It tracks dimensions such as:

- completeness
- validity
- uniqueness
- consistency
- accuracy

These can be retrieved through the API and are based on actual stored data rather than static files.

## Testing

Run the automated test suite locally with:

```bash
uv run pytest --cov=src --cov-report=term-missing
```

Run the tests inside the Dockerized app container:

```bash
docker compose run --rm api uv run pytest --cov=src --cov-report=term-missing
```

The test suite covers:

- client retry and pagination behavior
- schema validation logic
- repository and quarantine persistence
- API routes and error handling
- quality metric calculations

## Design Notes

A few implementation choices are important to understand:

- No ORM is used; raw parameterized SQL is used for database operations.
- Invalid records are quarantined with raw payloads and error metadata for traceability.
- Duplicate quarantine prevention is enforced using a payload hash keyed by organization.
- A unique index prevents multiple simultaneous runs for the same organization.
- The pipeline is designed to be safe to rerun and robust against partial failures.

## License

This project is intended for internal or educational use as part of the business data insights assignment. The exact licensing terms should be confirmed before external distribution.

## Summary

This repository is a practical example of a data engineering pipeline: ingest raw API data, enforce quality controls, preserve operational logs, and expose both business and technical health signals through a clean API surface.

