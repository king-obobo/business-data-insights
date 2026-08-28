import os
from kaggle.api.kaggle_api_extended import KaggleApi

dataset_id = 'amangarg08/apple-retail-sales-dataset'
target_dir = './data/raw'


def download_kaggle_dataset(dataset_id, target_dir):
    os.makedirs(target_dir, exist_ok=True)

    if os.listdir(target_dir):
        print(f"The target directory: {target_dir} already exists. Skipping download.")
    else:
        api = KaggleApi()
        api.authenticate()
        print(f"Downloading dataset {dataset_id} to {target_dir}...")
        api.dataset_download_files(dataset_id, path=target_dir, unzip=True)
        print(f"Dataset {dataset_id} downloaded and extracted to {target_dir}.")
        
        
if __name__ == "__main__":
    download_kaggle_dataset(dataset_id, target_dir)