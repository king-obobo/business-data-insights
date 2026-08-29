from pathlib import Path
from .db import get_cursor
import os


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = PROJECT_ROOT / "db" / "schema.sql"


def create_schema(schema_file: Path = SCHEMA_PATH) -> None:
    
    print(f"Executing DDL script from '{schema_file}'...")
    
    if not os.path.exists(schema_file):
        raise FileNotFoundError("Schema file not found....")
    
    with open(schema_file, 'r', encoding='utf-8') as f:
        schema_sql = f.read()
        
    with get_cursor() as cur:
        cur.execute(schema_sql)
        
    print("Database schema successfully created")
    
    
# if __name__ == "__main__":
#     create_schema(schema_file=SCHEMA_PATH)