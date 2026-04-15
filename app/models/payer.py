from enum import Enum

from peewee import AutoField, CharField, Model, fn

from app.db import db


class PayerKind(str, Enum):
    INDIVIDUAL = "individual"
    BUSINESS = "business"


class Payer(Model):
    id = AutoField()
    name = CharField(max_length=150)
    document = CharField(max_length=20, unique=True)
    email = CharField(max_length=254, null=True)
    whatsapp = CharField(max_length=20, null=True)
    kind = CharField(
        max_length=12,
        choices=[(k.value, k.name) for k in PayerKind],
        default=PayerKind.INDIVIDUAL.value,
    )

    class Meta:
        database = db
        table_name = "payers"

    @classmethod
    def select_random(cls, count):
        return list(cls.select().order_by(fn.RANDOM()).limit(count))
