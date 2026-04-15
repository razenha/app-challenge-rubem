from urllib.parse import urlparse

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

from app.config import DATABASE_URL


def run():
    parsed = urlparse(DATABASE_URL)
    db_name = parsed.path.lstrip("/")

    conn = psycopg2.connect(
        host=parsed.hostname,
        port=parsed.port or 5432,
        user=parsed.username,
        password=parsed.password,
        dbname="postgres",
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

    cursor = conn.cursor()
    cursor.execute(f"SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))

    if cursor.fetchone():
        print(f"Database '{db_name}' already exists.")
    else:
        cursor.execute(f'CREATE DATABASE "{db_name}"')
        print(f"Database '{db_name}' created.")

    cursor.close()
    conn.close()


if __name__ == "__main__":
    run()
