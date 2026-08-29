from src.init_db import create_schema
from src.extract import load_all_data
from src.load import load_dataframes_to_db



if __name__ == "__main__":
    create_schema()
    
    print("==========LOADING DATA=================\n\n")
    
    all_data = load_all_data()

    sales_df = all_data['sales']
    products_df = all_data['products']
    stores_df = all_data['stores']
    category_df = all_data['category']
    warranty_df = all_data['warranty']
    
    print("============Loading into DB=================")
    load_dataframes_to_db(
        category_df= category_df,
        stores_df= stores_df,
        products_df= products_df,
        sales_df= sales_df,
        warranty_df= warranty_df
    )