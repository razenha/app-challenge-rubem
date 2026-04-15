import os

from peewee_migrate import Router

MIGRATE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "migrations")


def run_migrations(database):
    router = Router(database, migrate_dir=MIGRATE_DIR)
    router.run()


if __name__ == "__main__":
    from app.db import db

    db.connect()
    run_migrations(db)
    db.close()
    print("Migrations complete.")
