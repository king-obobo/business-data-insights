from src.transform import export_to_parquet, merge_all_data, create_derived_col
from src.extract import load_parquet, load_parquet_polars, load_all_data
from src.aggregate import (
    revenue_by_year,
    revenue_by_category,
    top_3_prods_by_volume,
    top_3_prods_by_revenue,
    top_3_prods_by_revenue_polars
)
from scripts.download_data import download_kaggle_dataset, convert_stores_to_json


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
    
    print("Merging Data...\n")
    df = merge_all_data(sales_df=sales_df, products_df= products_df, stores_df= stores_df)
    
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