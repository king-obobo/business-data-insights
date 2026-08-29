import os
import time
import tracemalloc
import pandas as pd
import polars as pl
from aggregate import top_3_prods_by_revenue, top_3_prods_by_revenue_polars


def measure_execution(func, *args) -> tuple[any, float, float]:
    """
    Executes a function and measures:
    - Execution time (in milliseconds)
    - Peak memory allocation during execution (in Megabytes)
    """
    tracemalloc.start()
    start_time = time.perf_counter()

    result = func(*args)

    elapsed_ms = (time.perf_counter() - start_time) * 1000.0
    _, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    peak_mb = peak_bytes / (1024 * 1024)
    return result, elapsed_ms, peak_mb


def benchmark_data_loading(
    parquet_path: str, runs: int = 3
) -> dict[str, dict[str, float]]:
    """Benchmarks reading a Parquet file using Pandas vs Polars."""
    print(f"\n--- 1. Data-Loading Benchmark ({runs} runs) ---")
    print(f"Source file: {parquet_path}")

    # Pandas Loading
    pd_times, pd_mems = [], []
    for _ in range(runs):
        _, duration, memory = measure_execution(pd.read_parquet, parquet_path)
        pd_times.append(duration)
        pd_mems.append(memory)

    avg_pd_time = sum(pd_times) / runs
    avg_pd_mem = sum(pd_mems) / runs

    # Polars Loading
    pl_times, pl_mems = [], []
    for _ in range(runs):
        _, duration, memory = measure_execution(pl.read_parquet, parquet_path)
        pl_times.append(duration)
        pl_mems.append(memory)

    avg_pl_time = sum(pl_times) / runs
    avg_pl_mem = sum(pl_mems) / runs

    time_speedup = avg_pd_time / avg_pl_time if avg_pl_time > 0 else 0

    print(f"Pandas | Read Time: {avg_pd_time:7.2f} ms | Peak Memory: {avg_pd_mem:6.2f} MB")
    print(f"Polars | Read Time: {avg_pl_time:7.2f} ms | Peak Memory: {avg_pl_mem:6.2f} MB")
    print(f"--> Polars loaded the Parquet file {time_speedup:.2f}x faster.")

    return {
        "pandas": {"time_ms": avg_pd_time, "peak_memory_mb": avg_pd_mem},
        "polars": {"time_ms": avg_pl_time, "peak_memory_mb": avg_pl_mem},
    }


def benchmark_aggregation(
    pandas_df: pd.DataFrame, polars_df: pl.DataFrame, runs: int = 5
) -> dict[str, dict[str, float]]:
    """Benchmarks grouping and aggregating performance on in-memory DataFrames."""
    print(f"\n--- 2. Aggregation Benchmark ({runs} runs) ---")
    print(f"Dataset Rows: {len(pandas_df):,}")

    # Pandas Aggregation
    pd_times, pd_mems = [], []
    for _ in range(runs):
        _, duration, memory = measure_execution(top_3_prods_by_revenue, pandas_df)
        pd_times.append(duration)
        pd_mems.append(memory)

    avg_pd_time = sum(pd_times) / runs
    avg_pd_mem = sum(pd_mems) / runs

    # Polars Aggregation
    pl_times, pl_mems = [], []
    for _ in range(runs):
        _, duration, memory = measure_execution(top_3_prods_by_revenue_polars, polars_df)
        pl_times.append(duration)
        pl_mems.append(memory)

    avg_pl_time = sum(pl_times) / runs
    avg_pl_mem = sum(pl_mems) / runs

    time_speedup = avg_pd_time / avg_pl_time if avg_pl_time > 0 else 0

    print(f"Pandas | Exec Time: {avg_pd_time:7.2f} ms | Peak Memory: {avg_pd_mem:6.2f} MB")
    print(f"Polars | Exec Time: {avg_pl_time:7.2f} ms | Peak Memory: {avg_pl_mem:6.2f} MB")
    print(f"--> Polars completed aggregation {time_speedup:.2f}x faster.")

    return {
        "pandas": {"time_ms": avg_pd_time, "peak_memory_mb": avg_pd_mem},
        "polars": {"time_ms": avg_pl_time, "peak_memory_mb": avg_pl_mem},
    }


if __name__ == "__main__":
    # Resolves absolute path to align with your transform module
    DATA_DIR = os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'data', 'processed')
    )
    parquet_file = os.path.join(DATA_DIR, 'cleaned_data.parquet')

    if os.path.exists(parquet_file):
        # 1. Run Data Loading Benchmark
        load_results = benchmark_data_loading(parquet_file, runs=3)

        # 2. Load DataFrames into memory for execution benchmarking
        df_pd = pd.read_parquet(parquet_file)
        df_pl = pl.read_parquet(parquet_file)

        # 3. Run Aggregation Benchmark
        agg_results = benchmark_aggregation(df_pd, df_pl, runs=5)
    else:
        print(f"Parquet file not found at '{parquet_file}'. Please run main.py first.")