import io
import pandas as pd
import psycopg
from .db import get_cursor

# from extract import load_all_data


def copy_dataframe_in_chunks(
    cur: psycopg.Cursor,
    df: pd.DataFrame,
    table_name: str,
    columns: list[str],
    chunk_size: int = 100_000,
) -> None:
    """Streams a DataFrame directly into PostgreSQL via psycopg3 COPY."""
    total_rows = len(df)
    col_names = ", ".join(columns)
    copy_query = f"COPY {table_name} ({col_names}) FROM STDIN WITH (FORMAT text, NULL '\\N')"

    print(f"Loading {total_rows:,} rows into '{table_name}' table...")

    for start_idx in range(0, total_rows, chunk_size):
        chunk = df.iloc[start_idx : start_idx + chunk_size][columns].copy()


        buffer = io.StringIO()
        chunk.to_csv(buffer, index=False, header=False, sep="\t", na_rep="\\N")
        buffer.seek(0)

        with cur.copy(copy_query) as copy:
            while data := buffer.read(16384):
                copy.write(data)

    print(f"Successfully loaded '{table_name}'.")


def load_dataframes_to_db(
    category_df: pd.DataFrame,
    stores_df: pd.DataFrame,
    products_df: pd.DataFrame,
    sales_df: pd.DataFrame,
    warranty_df: pd.DataFrame,
) -> None:
    """Bulk loads all 5 clean DataFrames into PostgreSQL in foreign key order."""
    print("\n--- Starting Direct Bulk Ingestion via psycopg3 COPY ---")

    with get_cursor() as cur:
        # 1. CATEGORY
        copy_dataframe_in_chunks(
            cur, category_df, "category", ["category_id", "category_name"]
        )

        # 2. STORES
        copy_dataframe_in_chunks(
            cur, stores_df, "stores", ["store_id", "store_name", "city", "country"]
        )

        # 3. PRODUCTS (product_id PK)
        copy_dataframe_in_chunks(
            cur,
            products_df,
            "products",
            ["product_id", "product_name", "category_id", "launch_date", "price"],
        )

        # 4. SALES (1M+ rows chunked, product_id )
        copy_dataframe_in_chunks(
            cur,
            sales_df,
            "sales",
            ["sale_id", "sale_date", "store_id", "product_id", "quantity"],
            chunk_size=100_000,
        )

        # 5. WARRANTY
        copy_dataframe_in_chunks(
            cur,
            warranty_df,
            "warranty",
            ["claim_id", "claim_date", "sale_id", "repair_status"],
        )

    print("All tables successfully loaded into database!")
    




# if __name__ == "__main__":
    
#     print("==========LOADING DATA=================")
    
#     all_data = load_all_data()

#     sales_df = all_data['sales']
#     products_df = all_data['products']
#     stores_df = all_data['stores']
#     category_df = all_data['category']
#     warranty_df = all_data['warranty']
    
#     print("============Loading into DB=================")
#     load_dataframes_to_db(
#         category_df= category_df,
#         stores_df= stores_df,
#         products_df= products_df,
#         sales_df= sales_df,
#         warranty_df= warranty_df
#     )