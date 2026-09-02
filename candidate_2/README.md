# Business Data Insights

A Python-based ETL (Extract, Transform, Load) and analytics pipeline designed to process raw business data, transform it, store it into a structured database, and generate actionable business insights and benchmarks.

---

## Table of Contents

- [Overview](#-overview)
- [Project Architecture & Directory Structure](#-project-architecture--directory-structure)
- [Tech Stack & Tooling](#tech-stack--tooling)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Environment Configuration](#environment-configuration)
- [Usage & Execution](#usage--execution)
  - [1. Data Download](#1-data-download)
  - [2. Database Initialization](#2-database-initialization)
  - [3. Running the Main Pipeline](#3-running-the-main-pipeline)
  - [4. Benchmarking & Analytics](#4-benchmarking--analytics)
- [Modules Overview](#modules-overview)

---

## Overview

The **Business Data Insights** project provides an end-to-end framework for ingesting raw datasets, applying transformations, interacting with SQL database schemas, performing business aggregations, and benchmarking performance across different data processing strategies.

---

## Project Architecture & Directory Structure

```text
business-data-insights/
├── db/
│   └── schema.sql             # SQL schema definitions for table creation
├── data/
│   ├── raw/                   # Ingested raw source data files (created when the )
│   └── processed/             # Cleaned and transformed datasets
├── notebooks/
│   └── playground.ipynb       # Interactive Jupyter notebook for exploratory data analysis
├── scripts/
│   └── download_data.py       # Utility script to fetch raw datasets
├── src/
│   ├── __init__.py            # Package initializer
│   ├── extract.py             # Data extraction modules
│   ├── transform.py           # Data transformation and cleaning logic
│   ├── load.py                # Database ingestion & loading operations
│   ├── aggregate.py           # Business metrics & aggregation functions
│   ├── db.py                  # Database connection & context management
│   ├── init_db.py             # Database setup helper
│   ├── repository.py          # Data access layer (Repository pattern)
│   └── benchmark.py           # Execution benchmarking and performance evaluation
├── .env.example               # Template for environment variables
├── .gitignore                 # Files and folders ignored by Git
├── .python-version            # Python runtime version identifier
├── main.py                    # Main execution script / entry point
├── create_schema_and_load.py  # A script to create schema and load data to POSTGRESQL
├── pyproject.toml             # Project dependencies and configuration
└── uv.lock                    # Dependency lockfile managed by uv
```

## Tech Stack & Tooling
Language: Python 3.10+

Dependency & Environment Management: uv

Database: SQL / Postgresql (managed via db.py & repository.py)

Data Engineering: ETL architecture (extract, transform, load, aggregate)

Analysis: Jupyter Notebooks (playground.ipynb)
## Getting Started
### Prerequisites
* Python 3.10+
* Postgresql
* uv installed on your system:

### Installation
Clone the repository:
```bash
git clone <repository-url>
cd business-data-insights
cd candidate 2
```
Sync dependencies using uv:

```Bash
uv sync
```
This automatically sets up a virtual environment (.venv) and installs all locked dependencies.

### Environment Configuration
Copy the sample environment file and configure any necessary database URIs or credentials:
```Bash
cp .env.example .env
```
Modify .env as appropriate for your local or remote database settings.

## Usage & Execution
### 1. Data Download
    
Fetch raw data into the data/raw/ directory:
```bash
uv run python scripts/download_data.py
```

### 2. Database Initialization

Provision the database tables using the schema defined in db/schema.sql:

```Bash
uv run python src/init_db.py
```
### 3. Running the Main PipelineExecute the full ETL flow (Extract $\rightarrow$ Transform $\rightarrow$ Load $\rightarrow$ Aggregate):
```Bashuv 
run python main.py
```

### 4. Benchmarking & Analytics

Run performance benchmarks to measure data processing times and query efficiency:

```Bash
uv run python src/benchmark.py
```
```Text
--- 1. Data-Loading Benchmark (3 runs) ---
Pandas | Read Time:  147.17 ms | Peak Memory:  19.92 MB
Polars | Read Time:   86.46 ms | Peak Memory:   0.00 MB
--> Polars loaded the Parquet file 1.70x faster.

--- 2. Aggregation Benchmark (5 runs) ---
Dataset Rows: 1,040,200
Pandas | Exec Time:  133.01 ms | Peak Memory:  72.94 MB
Polars | Exec Time:   32.21 ms | Peak Memory:   0.01 MB
--> Polars completed aggregation 4.13x faster.
```
## Modules Overview

| File | Purpose |
| :--- | :--- |
| `src/extract.py` | Handles extraction of raw data from sources (CSV, API, etc.). |
| `src/transform.py` | Contains data validation, cleaning, and business transformation rules. |
| `src/load.py` | Orchestrates insertion of processed data into the database. |
| `src/repository.py` | Provides abstract query methods for interacting with database tables. |
| `src/aggregate.py` | Calculates high-level metrics, KPIs, and data summaries. |
| `src/benchmark.py` | Measures execution times across various ETL pipeline steps. |
| `src/db.py` | Connection pooling and session context handlers. |