from urllib.parse import urlparse

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

from app.config import DATABASE_URL


def run():
    parsed = urlparse(DATABASE_URL)
    db_name = parsed.path.lstrip("/")

    confirm = input(f"WARNING: This will permanently drop the database '{db_name}'. Type the database name to confirm: ")
    if confirm != db_name:
        print("Aborted.")
        return

    conn = psycopg2.connect(
        host=parsed.hostname,
        port=parsed.port or 5432,
        user=parsed.username,
        password=parsed.password,
        dbname="postgres",
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))

    if not cursor.fetchone():
        print(f"Database '{db_name}' does not exist.")
    else:
        cursor.execute(f'DROP DATABASE "{db_name}"')
        print(f"Database '{db_name}' dropped.")

    cursor.close()
    conn.close()


if __name__ == "__main__":
    run()
