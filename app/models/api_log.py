import datetime
from enum import Enum

from peewee import AutoField, CharField, DateTimeField, IntegerField, Model
from playhouse.postgres_ext import BinaryJSONField

from app.db import db


class LogDirection(str, Enum):
    INCOMING = "incoming"
    OUTGOING = "outgoing"


class ApiLog(Model):
    id = AutoField()
    direction = CharField(
        max_length=10,
        choices=[(d.value, d.name) for d in LogDirection],
    )
    method = CharField(max_length=10)
    url = CharField(max_length=2048)
    status_code = IntegerField(null=True)
    headers = BinaryJSONField(default=dict)
    body = BinaryJSONField(default=dict)
    created_at = DateTimeField(default=datetime.datetime.now)

    class Meta:
        database = db
        table_name = "api_logs"
