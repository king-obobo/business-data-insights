import os
from contextlib import contextmanager
from psycopg import Connection

import psycopg
from dotenv import load_dotenv


load_dotenv()

DB_URL= os.getenv("DATABASE_URL")


def get_db_connection():
    return psycopg.connect(DB_URL)


@contextmanager
def get_cursor():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            yield cur
            conn.commit()
