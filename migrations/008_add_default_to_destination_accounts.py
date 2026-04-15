"""Add default flag to destination_accounts table."""

import peewee as pw


def migrate(migrator, database, fake=False, **kwargs):
    migrator.add_fields(
        "destination_accounts",
        default=pw.BooleanField(default=False),
    )


def rollback(migrator, database, fake=False, **kwargs):
    migrator.remove_fields("destination_accounts", "default")
