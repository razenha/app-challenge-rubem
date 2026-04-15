"""Create payers table."""

import peewee as pw


def migrate(migrator, database, fake=False, **kwargs):
    @migrator.create_model
    class Payer(pw.Model):
        id = pw.AutoField()
        name = pw.CharField(max_length=150)
        document = pw.CharField(max_length=20, unique=True)
        email = pw.CharField(max_length=254, null=True)
        whatsapp = pw.CharField(max_length=20, null=True)
        kind = pw.CharField(max_length=12, default="individual")

        class Meta:
            table_name = "payers"


def rollback(migrator, database, fake=False, **kwargs):
    migrator.remove_model("payers")
