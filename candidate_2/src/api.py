# src/api.py
import uuid
import psycopg
from fastapi import FastAPI, HTTPException, BackgroundTasks
from uuid import UUID

from main import start_run, process_run
from .repository import (
    get_connection, get_connection, 
    get_run, list_runs, list_quarantine
)

from .client import GitHubClient
from .quality import compute_quality_report



app = FastAPI(title="GitHub Ingestion Pipeline")


@app.get("/quality-report/{org}")
def get_quality_report(org: str):
    with get_connection() as conn:
        report = compute_quality_report(conn, GitHubClient(), org)

    if report is None:
        raise HTTPException(
            status_code=404,
            detail=f"No completed ingestion run found for org '{org}'",
        )

    return report


@app.get("/runs/{run_id}")
def read_run(run_id: UUID):
    with get_connection() as conn:
        run = get_run(conn, run_id)

    if run is None:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")

    return run


@app.get("/runs")
def read_runs():
    with get_connection() as conn:
        runs = list_runs(conn)
    return runs

@app.post("/ingest/{org}")
def ingest_org(org: str, background_tasks: BackgroundTasks):
    try:
        run_id = start_run(org)
    except psycopg.errors.UniqueViolation:
        raise HTTPException(
            status_code=409,
            detail=f"An ingestion run is already in progress for org '{org}'",
        )

    background_tasks.add_task(process_run, run_id, org)
    return {"run_id": str(run_id), "org": org, "status": "running"}


@app.get("/quarantine/{org}")
def read_quarantine(org: str, page: int = 1, page_size: int = 20):
    with get_connection() as conn:
        return list_quarantine(conn, org, page=page, page_size=page_size)