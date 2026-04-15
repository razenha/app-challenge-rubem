"""Add correlation_id (idempotency-like key via tags) to invoices table."""

import peewee as pw


def migrate(migrator, database, fake=False, **kwargs):
    migrator.add_fields(
        "invoices",
        correlation_id=pw.CharField(max_length=36, unique=True, null=True),
    )


def rollback(migrator, database, fake=False, **kwargs):
    migrator.remove_fields("invoices", "correlation_id")
