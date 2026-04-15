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
from app.models.destination_account import DestinationAccount
from app.models.exceptions import InvalidStatusTransitionError
from app.models.invoice import Invoice


class TransferStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    CREATED = "created"
    PROCESSING = "processing"
    SUCCESS = "success"
    CANCELED = "canceled"
    FAILED = "failed"


# SUCCESS, CANCELED e FAILED são terminais — não aparecem como chave.
# Mesmo status é tratado como no-op (idempotência).
_VALID_TRANSFER_TRANSITIONS = {
    TransferStatus.PENDING.value: {TransferStatus.SENT.value, TransferStatus.CREATED.value, TransferStatus.FAILED.value},
    TransferStatus.SENT.value: {
        TransferStatus.CREATED.value,
        TransferStatus.PROCESSING.value,
        TransferStatus.CANCELED.value,
        TransferStatus.FAILED.value,
    },
    TransferStatus.CREATED.value: {
        TransferStatus.PROCESSING.value,
        TransferStatus.SUCCESS.value,
        TransferStatus.CANCELED.value,
        TransferStatus.FAILED.value,
    },
    TransferStatus.PROCESSING.value: {TransferStatus.SUCCESS.value, TransferStatus.FAILED.value, TransferStatus.CANCELED.value},
}


class Transfer(Model):
    id = AutoField()
    stark_id = CharField(max_length=64, unique=True, null=True)
    external_id = CharField(max_length=36, unique=True, default=lambda: str(uuid.uuid4()))
    invoice = ForeignKeyField(Invoice, backref="transfers")
    destination_account = ForeignKeyField(DestinationAccount, backref="transfers")
    amount = IntegerField()
    status = CharField(
        max_length=12,
        choices=[(s.value, s.name) for s in TransferStatus],
        default=TransferStatus.PENDING.value,
    )
    created_at = DateTimeField(default=datetime.datetime.now)

    class Meta:
        database = db
        table_name = "transfers"

    # ----- Transições de status -----
    #
    # Apenas alteram campos em memória; o caller persiste.

    def mark_as_created(self, stark_id):
        self._transition_to(TransferStatus.CREATED.value)
        self.stark_id = stark_id

    def mark_as_processing(self, stark_id):
        self._transition_to(TransferStatus.PROCESSING.value)
        self.stark_id = stark_id

    def mark_as_success(self, stark_id):
        self._transition_to(TransferStatus.SUCCESS.value)
        self.stark_id = stark_id

    def mark_as_canceled(self, stark_id):
        self._transition_to(TransferStatus.CANCELED.value)
        self.stark_id = stark_id

    def mark_as_failed(self, stark_id):
        self._transition_to(TransferStatus.FAILED.value)
        self.stark_id = stark_id

    def _transition_to(self, target_status):
        if self.status == target_status:
            return  # idempotência: mesmo estado é no-op
        allowed = _VALID_TRANSFER_TRANSITIONS.get(self.status, set())
        if target_status not in allowed:
            raise InvalidStatusTransitionError(self, self.status, target_status)
        self.status = target_status
