import os
import pandas as pd


DATA_DIR = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__), '..', 'data', 'raw'
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
    return pd.read_csv(
        file_path,
        parse_dates=['Launch_Date'],
        date_format='%Y-%m-%d',
        dtype = {'Price': 'Int32'}
    )
    

def load_stores(data_dir: str = DATA_DIR) -> pd.DataFrame:
    """Loads the JSON stores dataset

    Args:
        data_dir (str, optional): _description_. Defaults to DATA_DIR.

    Returns:
        pd.DataFrame: _description_
    """
    file_path = os.path.join(data_dir, 'stores.json')
    return pd.read_json(file_path)


def load_warranty(data_dir: str) -> pd.DataFrame:
    """Load and parse the warrant claims dataset"""
    file_path = os.path.join(data_dir, 'warranty.csv')
    return pd.read_csv(file_path, parse_dates=['claim_date'], date_format='%Y-%m-%d')


def load_all_data(data_dir: str = DATA_DIR) -> dict[str, pd.DataFrame]:
    """Loads all raw detail datasets into a dictionary"""
    return {
        'sales': load_sales(data_dir),
        'products': load_products(data_dir),
        'stores': load_stores(data_dir),
        'warranty': load_warranty(data_dir),
    }
    
    
if __name__ == '__main__':
    data = load_all_data()
    
    for name, df in data.items():
        print(f"Loaded {name}: {df.shape[0]} rows, {df.shape[1]} columns")