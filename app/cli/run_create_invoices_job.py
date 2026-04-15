from app.db import db
from app.starkbank_setup import init_starkbank
from app.jobs.invoices import create_invoices


def run():
    init_starkbank()
    db.connect()

    count = create_invoices.call_local()

    db.close()
    print(f"{count} invoices created.")


if __name__ == "__main__":
    run()
