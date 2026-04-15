"""Create api_logs table."""

import peewee as pw
from playhouse.postgres_ext import BinaryJSONField


def migrate(migrator, database, fake=False, **kwargs):
    @migrator.create_model
    class ApiLog(pw.Model):
        id = pw.AutoField()
        direction = pw.CharField(max_length=10)
        method = pw.CharField(max_length=10)
        url = pw.CharField(max_length=2048)
        status_code = pw.IntegerField(null=True)
        headers = BinaryJSONField(default=dict)
        body = BinaryJSONField(default=dict)
        created_at = pw.DateTimeField()

        class Meta:
            table_name = "api_logs"


def rollback(migrator, database, fake=False, **kwargs):
    migrator.remove_model("api_logs")
