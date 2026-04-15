from enum import Enum

from peewee import AutoField, BooleanField, CharField, Model

from app.db import db


class AccountType(str, Enum):
    CHECKING = "checking"
    SAVINGS = "savings"
    SALARY = "salary"
    PAYMENT = "payment"


class DestinationAccount(Model):
    id = AutoField()
    bank_code = CharField(max_length=8)
    branch = CharField(max_length=10)
    account_number = CharField(max_length=20)
    name = CharField(max_length=150)
    tax_id = CharField(max_length=20)
    account_type = CharField(
        max_length=10,
        choices=[(t.value, t.name) for t in AccountType],
    )
    default = BooleanField(default=False)

    class Meta:
        database = db
        table_name = "destination_accounts"

    @classmethod
    def get_default(cls):
        account = cls.get_or_none(cls.default == True)  # noqa: E712
        if account is None:
            raise RuntimeError(
                "No default DestinationAccount found. "
            )
        return account
