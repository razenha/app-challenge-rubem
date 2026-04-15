"""Factory-boy factories for Peewee models.

Uses `factory.Factory` (base) and delegates creation to the model's `.create()`,
since factory-boy doesn't have first-class Peewee support.
"""

import factory
from factory import Faker, LazyAttribute, SubFactory

from app.models.destination_account import AccountType, DestinationAccount
from app.models.invoice import Invoice, InvoiceStatus
from app.models.payer import Payer, PayerKind
from app.models.transfer import Transfer, TransferStatus


class PeeweeModelFactory(factory.Factory):
    class Meta:
        abstract = True

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        return model_class.create(*args, **kwargs)


class PayerFactory(PeeweeModelFactory):
    class Meta:
        model = Payer

    name = Faker("name", locale="pt_BR")
    document = factory.Sequence(lambda n: f"{n:011d}")
    email = Faker("email")
    whatsapp = Faker("phone_number", locale="pt_BR")
    kind = PayerKind.INDIVIDUAL.value


class DestinationAccountFactory(PeeweeModelFactory):
    class Meta:
        model = DestinationAccount

    bank_code = "20018183"
    branch = "0001"
    account_number = factory.Sequence(lambda n: f"{6341320293482000 + n}")
    name = "Stark Bank S.A."
    tax_id = "20.018.183/0001-80"
    account_type = AccountType.PAYMENT.value
    default = False


class InvoiceFactory(PeeweeModelFactory):
    class Meta:
        model = Invoice

    payer = SubFactory(PayerFactory)
    amount = 10000
    status = InvoiceStatus.PENDING.value
    stark_id = None  # simulates invoice not yet sent to Stark Bank
    # correlation_id uses the model default (UUID)


def _ensure_default_destination_account():
    existing = DestinationAccount.get_or_none(DestinationAccount.default == True)  # noqa: E712
    if existing:
        return existing
    return DestinationAccountFactory(default=True)


class TransferFactory(PeeweeModelFactory):
    class Meta:
        model = Transfer

    invoice = SubFactory(InvoiceFactory)
    destination_account = LazyAttribute(lambda _: _ensure_default_destination_account())
    amount = 10000
    status = TransferStatus.PENDING.value
    stark_id = None
    # external_id uses the model default (UUID)
