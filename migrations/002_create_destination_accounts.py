"""Create destination_accounts table."""

import peewee as pw


def migrate(migrator, database, fake=False, **kwargs):
    @migrator.create_model
    class DestinationAccount(pw.Model):
        id = pw.AutoField()
        bank_code = pw.CharField(max_length=8)
        branch = pw.CharField(max_length=10)
        account_number = pw.CharField(max_length=20)
        name = pw.CharField(max_length=150)
        tax_id = pw.CharField(max_length=20)
        account_type = pw.CharField(max_length=20)

        class Meta:
            table_name = "destination_accounts"


def rollback(migrator, database, fake=False, **kwargs):
    migrator.remove_model("destination_accounts")
