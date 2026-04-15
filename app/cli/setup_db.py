from app.cli.create_db import run as create_db
from app.cli.migrate import run_migrations
from app.cli.seed import run as seed
from app.db import db


def run():
    print("==> Creating database...")
    create_db()

    print("==> Running migrations...")
    db.connect()
    run_migrations(db)
    db.close()

    print("==> Seeding data...")
    seed()

    print("==> Setup complete.")


if __name__ == "__main__":
    run()
