import os
import pandas as pd


DATA_DIR = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__), '..', 'data', 'processed'
    )
)


# I will not be using the warranty df

# Merge the data
def merge_all_data(
    sales_df: pd.DataFrame,
    products_df: pd.DataFrame,
    stores_df: pd.DataFrame
) -> pd.DataFrame:
    unified_df = sales_df.merge(products_df, on='product_id', how='left')
    
    unified_df = unified_df.merge(stores_df, on='store_id', how='left')
    
    return unified_df

# Derive revenue column
def create_derived_col(df: pd.DataFrame) -> pd.DataFrame:
    df['revenue'] = df['quantity'] * df['price']
    return df


# Export to parquet
def export_to_parquet(df: pd.DataFrame) -> None:
    if DATA_DIR:
        print("File already exists, skipping conversion to parquet step...")
        return
    os.makedirs(DATA_DIR, exist_ok=True)
    df.to_parquet(f"{DATA_DIR}/cleaned_data.parquet", engine='pyarrow', index=False)
    print("Succesfully exported to Parquet")
    
    
    
# if __name__ == '__main__':
#     print("Loading Data ... \n")
#     all_data = load_all_data()

#     sales_df = all_data.get('sales')
#     products_df = all_data.get('products')
#     stores_df = all_data.get('stores')
    
#     print("Merging Data...\n")
#     df = merge_all_data(sales_df=sales_df, products_df= products_df, stores_df= stores_df)
    
#     df = create_derived_col(df)
    
#     # Export to Parquet
#     export_to_parquet(df)
        
    