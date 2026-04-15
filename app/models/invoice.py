import datetime
import uuid
from enum import Enum

from peewee import (
    AutoField,
    CharField,
    DateTimeField,
    ForeignKeyField,
    IntegerField,
    Model,
)

from app.db import db
from app.models.exceptions import InvalidStatusTransitionError
from app.models.payer import Payer


CORRELATION_TAG_PREFIX = "correlation:"


class InvoiceStatus(str, Enum):
    # Indica que a invoice ainda não foi enviada ao Stark Bank
    PENDING = "pending"

    # Indica que a invoice foi enviada para o Stark Bank, mas ainda não recebeu o retorno do webhook que ela foi criada.
    SENT = "sent"

    # Status da API de Invoices do Stark Bank
    CREATED = "created"
    PAID = "paid"
    CREDITED = "credited"
    CANCELED = "canceled"
    OVERDUE = "overdue"
    EXPIRED = "expired"


# Workflow permitido. Estados terminais (CREDITED, CANCELED, EXPIRED) não
# aparecem como chave porque não admitem transição para nenhum outro status.
# Transições para o mesmo status são tratadas como no-op (idempotência).
_VALID_INVOICE_TRANSITIONS = {
    InvoiceStatus.PENDING.value: {InvoiceStatus.SENT.value, InvoiceStatus.CREATED.value, InvoiceStatus.CANCELED.value},
    InvoiceStatus.SENT.value: {InvoiceStatus.CREATED.value, InvoiceStatus.CANCELED.value},
    InvoiceStatus.CREATED.value: {
        InvoiceStatus.PAID.value,
        InvoiceStatus.CREDITED.value,
        InvoiceStatus.CANCELED.value,
        InvoiceStatus.OVERDUE.value,
    },
    InvoiceStatus.PAID.value: {InvoiceStatus.CREDITED.value},
    InvoiceStatus.OVERDUE.value: {
        InvoiceStatus.PAID.value,
        InvoiceStatus.CANCELED.value,
        InvoiceStatus.EXPIRED.value,
    },
}


class Invoice(Model):
    id = AutoField()
    stark_id = CharField(max_length=64, unique=True, null=True)

    # correlation_id: Chave de identificação que é enviada no campo tag da API do Stark Bank para correlacionar a invoice local com a invoice do Stark Bank. Formato: "correlation:{uuid}"
    # Em raras ocasiões, a API do Stark Bank pode chamar o webhook de invoice antes dessa app atualizar a invoice local com o stark_id,
    # fazendo com que o callback não encontre a invoice local usando o campo stark_id.
    # O campo correlation_id é usado para encontrar a invoice local mesmo nesses casos, usando o valor enviado no campo tag da API do Stark Bank.
    # Ainda pode ser usado para verificar casos de invoices sendo criada em duplicidade.
    correlation_id = CharField(max_length=36, unique=True, default=lambda: str(uuid.uuid4()))
    payer = ForeignKeyField(Payer, backref="invoices")
    amount = IntegerField()
    status = CharField(
        max_length=10,
        choices=[(s.value, s.name) for s in InvoiceStatus],
        default=InvoiceStatus.PENDING.value,
    )
    processing_fee = IntegerField(default=0, null=True)
    created_at = DateTimeField(default=datetime.datetime.now)
    updated_at = DateTimeField(default=datetime.datetime.now)

    class Meta:
        database = db
        table_name = "invoices"

    # ----- Transições de status -----
    #
    # Os métodos abaixo apenas alteram os campos em memória (não chamam .save()).
    # O caller é responsável por persistir.

    def mark_as_created(self, stark_id):
        self._transition_to(InvoiceStatus.CREATED.value)
        self.stark_id = stark_id

    def mark_as_paid(self, stark_id, processing_fee):
        self._transition_to(InvoiceStatus.PAID.value)
        self.stark_id = stark_id
        self.processing_fee = processing_fee

    def mark_as_credited(self, stark_id, processing_fee):
        self._transition_to(InvoiceStatus.CREDITED.value)
        self.stark_id = stark_id
        self.processing_fee = processing_fee

    def mark_as_canceled(self, stark_id):
        self._transition_to(InvoiceStatus.CANCELED.value)
        self.stark_id = stark_id

    def mark_as_overdue(self, stark_id):
        self._transition_to(InvoiceStatus.OVERDUE.value)
        self.stark_id = stark_id

    def mark_as_expired(self, stark_id):
        self._transition_to(InvoiceStatus.EXPIRED.value)
        self.stark_id = stark_id

    def _transition_to(self, target_status):
        if self.status == target_status:
            return  # idempotência: mesmo estado é no-op
        allowed = _VALID_INVOICE_TRANSITIONS.get(self.status, set())
        if target_status not in allowed:
            raise InvalidStatusTransitionError(self, self.status, target_status)
        self.status = target_status
