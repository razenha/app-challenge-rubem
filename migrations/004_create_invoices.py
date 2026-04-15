"""Create invoices table."""

import peewee as pw


def migrate(migrator, database, fake=False, **kwargs):
    Payer = migrator.orm["payers"]

    @migrator.create_model
    class Invoice(pw.Model):
        id = pw.AutoField()
        stark_id = pw.CharField(max_length=64, unique=True, null=True)
        payer = pw.ForeignKeyField(Payer, column_name="payer_id", on_delete="CASCADE")
        amount = pw.IntegerField()
        status = pw.CharField(max_length=20, default="created")
        fee = pw.IntegerField(default=0)
        created_at = pw.DateTimeField()
        updated_at = pw.DateTimeField()

        class Meta:
            table_name = "invoices"


def rollback(migrator, database, fake=False, **kwargs):
    migrator.remove_model("invoices")
