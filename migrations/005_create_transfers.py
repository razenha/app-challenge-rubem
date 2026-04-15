"""Create transfers table."""

import peewee as pw


def migrate(migrator, database, fake=False, **kwargs):
    Invoice = migrator.orm["invoices"]
    DestinationAccount = migrator.orm["destination_accounts"]

    @migrator.create_model
    class Transfer(pw.Model):
        id = pw.AutoField()
        stark_id = pw.CharField(max_length=64, unique=True, null=True)
        invoice = pw.ForeignKeyField(Invoice, column_name="invoice_id", on_delete="CASCADE")
        destination_account = pw.ForeignKeyField(DestinationAccount, column_name="destination_account_id", on_delete="CASCADE")
        amount = pw.IntegerField()
        status = pw.CharField(max_length=20, default="created")
        created_at = pw.DateTimeField()

        class Meta:
            table_name = "transfers"


def rollback(migrator, database, fake=False, **kwargs):
    migrator.remove_model("transfers")
