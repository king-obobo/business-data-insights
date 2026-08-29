from src.transform import export_to_parquet, merge_all_data, create_derived_col
from src.extract import load_parquet, load_parquet_polars, load_all_data
from src.aggregate import (
    revenue_by_year,
    revenue_by_category,
    top_3_prods_by_volume,
    top_3_prods_by_revenue,
    top_3_prods_by_revenue_polars
)

from src.init_db import create_schema
from src.extract import load_all_data
from src.load import load_dataframes_to_db

from scripts.download_data import download_kaggle_dataset, convert_stores_to_json
from src.repository import SalesRepository


dataset_id = 'amangarg08/apple-retail-sales-dataset'
target_dir = './data/raw'

if __name__ == "__main__":
    # Download the dataset 
    download_kaggle_dataset(dataset_id, target_dir)
    
    # converting stores.csv to stores.json
    convert_stores_to_json(target_dir)
    
    # Loading all data
    print("Loading Data ... \n")
    all_data = load_all_data()

    sales_df = all_data['sales']
    products_df = all_data['products']
    stores_df = all_data['stores']
    category_df = all_data['category']
    warranty_df = all_data['warranty']
    
    print("Merging Data...\n")
    df = merge_all_data(sales_df=sales_df, products_df= products_df, stores_df= stores_df, category_df= category_df)
    
    df = create_derived_col(df)
    
    # Export to Parquet
    export_to_parquet(df)
    
    # Reading in the parquet file and using it for aggregations
    df = load_parquet()
    pl_df = load_parquet_polars()
    
    print("\n======REVENUE BY YEAR==========")
    print(revenue_by_year(df))
    
    print("\n======REVENUE BY CATEGORY==========")
    print(revenue_by_category(df))
    
    print("\n======TOP 3 PRODUCTS BY VOLUME==========")
    print(top_3_prods_by_volume(df))

    print("\n======TOP 3 PRODUCTS BY REVENUE PANDAS==========")
    print(top_3_prods_by_revenue(df))
    
    print("\n======TOP 3 PRODUCTS BY REVENUE POLARS==========")
    print(top_3_prods_by_revenue_polars(pl_df))
    
    # Creating the schema and loading the data into the db
    create_schema()
    
    print("============Loading into DB=================")
    load_dataframes_to_db(
        category_df= category_df,
        stores_df= stores_df,
        products_df= products_df,
        sales_df= sales_df,
        warranty_df= warranty_df
    )
    
    # Rinning the queries from the loaded data in my DB
    repo = SalesRepository()
    # 1. Top 3 Products per Store (Window Function)
    print("\n================ TOP 3 PRODUCTS PER STORE BY REVENUE ================")
    top_products_df = repo.get_top_products_per_store(rank_limit=3)
    print(top_products_df.head(10))

    # 2. Warranty Claim Rate by Category (CTE Join)
    print("\n============== WARRANTY CLAIM RATE BY CATEGORY ==============")
    claim_rate_df = repo.get_claim_rate_by_category()
    print(claim_rate_df)
    