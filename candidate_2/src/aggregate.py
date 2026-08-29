import pandas as pd
import polars as pl
# from .extract import load_parquet, load_parquet_polars


# df = load_parquet()
# pl_df = load_parquet_polars()


def revenue_by_year(df:pd.DataFrame) -> pd.DataFrame :
    yearly_revenue = (
        df.groupby(df['sale_date'].dt.to_period('Y'))['revenue']
        .sum()
        .reset_index()
        .rename(columns={'sale_date': 'sale_year'})
    )
    
    return yearly_revenue


def revenue_by_category(df: pd.DataFrame) -> pd.DataFrame :
    category_revenue = (
        df.groupby('category_id')
        .agg(
            total_revenue= ('revenue', 'sum'), 
            total_units_sold = ('quantity', 'sum'), 
            transaction_count = ('sale_id', 'count')
        )
        .sort_values(by = 'total_revenue', ascending=False)
        .reset_index()
    )
    
    return category_revenue



def top_3_prods_by_volume(df: pd.DataFrame) -> pd.DataFrame :
    top_3_prods_by_vol = (
        df.groupby(['product_id', 'product_name'])
        .agg(total_units_sold= ('quantity', 'sum'))
        .sort_values(by = 'total_units_sold', ascending=False)
        .head(3)
        .reset_index()
    )
    return top_3_prods_by_vol


def top_3_prods_by_revenue(df: pd.DataFrame) -> pd.DataFrame :
    top_3_prods_rev = (
        df.groupby(['product_id', 'product_name'])
        .agg(total_revenue = ('revenue', 'sum'))
        .sort_values(by = 'total_revenue', ascending=False)
        .head(3)
        .reset_index()
    )
    return top_3_prods_rev


def top_3_prods_by_revenue_polars(pl_df: pl.DataFrame) -> pl.DataFrame:
    """Polars execution path for Top 3 Products by Revenue."""
    top_3_prods_rev = (
        pl_df.group_by(['product_id', 'product_name'])
        .agg(pl.col('revenue').sum().alias('total_revenue'))
        .sort('total_revenue', descending=True)
        .head(3)
    )
    return top_3_prods_rev


# if __name__ == '__main__':
#     df = load_parquet()
#     pl_df = load_parquet_polars()
    
#     print("\n======REVENUE BY YEAR==========")
#     print(revenue_by_year(df))
    
#     print("\n======REVENUE BY CATEGORY==========")
#     print(revenue_by_category(df))
    
#     print("\n======TOP 3 PRODUCTS BY VOLUME==========")
#     print(top_3_prods_by_volume(df))

#     print("\n======TOP 3 PRODUCTS BY REVENUE PANDAS==========")
#     print(top_3_prods_by_revenue(df))
    
#     print("\n======TOP 3 PRODUCTS BY REVENUE POLARS==========")
#     print(top_3_prods_by_revenue_polars(pl_df))