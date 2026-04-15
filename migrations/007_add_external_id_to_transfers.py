"""Add external_id (idempotency key) to transfers table."""

import peewee as pw


def migrate(migrator, database, fake=False, **kwargs):
    migrator.add_fields(
        "transfers",
        external_id=pw.CharField(max_length=36, unique=True, null=True),
    )


def rollback(migrator, database, fake=False, **kwargs):
    migrator.remove_fields("transfers", "external_id")
