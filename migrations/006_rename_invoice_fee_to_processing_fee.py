"""Rename invoices.fee to invoices.processing_fee."""


def migrate(migrator, database, fake=False, **kwargs):
    migrator.rename_field("invoices", "fee", "processing_fee")


def rollback(migrator, database, fake=False, **kwargs):
    migrator.rename_field("invoices", "processing_fee", "fee")
