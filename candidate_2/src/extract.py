import os
import pandas as pd
import polars as pl


DATA_DIR = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__), '..', 'data', 'raw'
    )
)

PARQUET_DIR = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__), '..', 'data', 'processed'
    )
)


def load_sales(data_dir: str = DATA_DIR) -> pd.DataFrame:
    """Loads and Parses the sales dataset

    Args:
        data_dir (str, optional): string repr. Defaults to DATA_DIR.

    Returns:
        pd.DataFrame: _description_
    """
    file_path = os.path.join(data_dir, 'sales.csv')
    return pd.read_csv(
        file_path,
        parse_dates=['sale_date'],
        date_format='%d-%m-%Y',
        dtype = {'quantity': 'Int32'}
    )
    
    
def load_products(data_dir: str = DATA_DIR) -> pd.DataFrame:
    """Loads and Parses the products dataset

    Args:
        data_dir (str, optional): string repr. Defaults to DATA_DIR.

    Returns:
        pd.DataFrame: _description_
    """
    file_path = os.path.join(data_dir, 'products.csv')
    df = pd.read_csv(
            file_path,
            parse_dates=['Launch_Date'],
            date_format='%Y-%m-%d',
            dtype = {'Price': 'Int32'}
        )
    df.columns = df.columns.str.lower()
    return df
    

def load_stores(data_dir: str = DATA_DIR) -> pd.DataFrame:
    """Loads the JSON stores dataset

    Args:
        data_dir (str, optional): _description_. Defaults to DATA_DIR.

    Returns:
        pd.DataFrame: _description_
    """
    file_path = os.path.join(data_dir, 'stores.json')
    df = pd.read_json(file_path)
    df.columns = df.columns.str.lower()
    return df


def load_warranty(data_dir: str) -> pd.DataFrame:
    """Load and parse the warrant claims dataset"""
    file_path = os.path.join(data_dir, 'warranty.csv')
    return pd.read_csv(file_path, parse_dates=['claim_date'], date_format='%Y-%m-%d')


def load_category(data_dir: str = DATA_DIR) -> pd.DataFrame:
    """Loads in a csv file

    Args:
        data_dir (str, optional):Defaults to DATA_DIR.

    Returns:
        pd.DataFrame: _description_
    """
    file_path = os.path.join(data_dir, 'category.csv')
    return pd.read_csv(file_path)


def load_all_data(data_dir: str = DATA_DIR) -> dict[str, pd.DataFrame]:
    """Loads all raw detail datasets into a dictionary"""
    return {
        'sales': load_sales(data_dir),
        'products': load_products(data_dir),
        'stores': load_stores(data_dir),
        'warranty': load_warranty(data_dir),
        'category': load_category(data_dir)
    }
    

def load_parquet(data_dir: str = PARQUET_DIR) -> pd.DataFrame:
    """Loads in a parquet file

    Args:
        data_dir (str, optional):Defaults to PARQUET_DIR.

    Returns:
        pd.DataFrame: _description_
    """
    file_path = os.path.join(data_dir, 'cleaned_data.parquet')
    return pd.read_parquet(file_path)


def load_parquet_polars(data_dir: str = PARQUET_DIR) -> pl.DataFrame :
    """_summary_

    Args:
        data_dir (str, optional):Defaults to PARQUET_DIR.

    Returns:
        pl.DataFrame: _description_
    """
    file_path = os.path.join(data_dir, 'cleaned_data.parquet')
    return pl.read_parquet(file_path)
    
    
# if __name__ == '__main__':
#     data = load_all_data()
    
#     for name, df in data.items():
#         print(f"Loaded {name}: {df.shape[0]} rows, {df.shape[1]} columns")