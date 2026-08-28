import os
from kaggle.api.kaggle_api_extended import KaggleApi
import pandas as pd

dataset_id = 'amangarg08/apple-retail-sales-dataset'
target_dir = './data/raw'


def download_kaggle_dataset(dataset_id: str, target_dir:str) -> None:
    os.makedirs(target_dir, exist_ok=True)

    if os.listdir(target_dir):
        print(f"The target directory: {target_dir} already exists. Skipping download.")
    else:
        api = KaggleApi()
        api.authenticate()
        print(f"Downloading dataset {dataset_id} to {target_dir}...")
        api.dataset_download_files(dataset_id, path=target_dir, unzip=True)
        print(f"Dataset {dataset_id} downloaded and extracted to {target_dir}.")


def convert_stores_to_json(target_dir: str) -> None:
    csv_path = os.path.join(target_dir, 'stores.csv')
    json_path = os.path.join(target_dir, 'stores.json')
    
    if os.path.exists(json_path):
        print(f"File {json_path} already exists. Skipping JSON Conversion")
        return
    
    if os.path.exists(csv_path):
        print(f"\nConverting {csv_path} to {json_path}... \n")
        stores_df = pd.read_csv(csv_path)
        
        stores_df.to_json(json_path, orient='records', indent=2)
        print(f"Successfully created {json_path}")
    
        
if __name__ == "__main__":
    #1. Download and unzip the data to the given directory
    download_kaggle_dataset(dataset_id, target_dir)
    
    #2. Convert stores.csv to store.json
    convert_stores_to_json(target_dir)