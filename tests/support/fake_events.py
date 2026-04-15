"""Builders for fake Stark Bank webhook events.

These return objects shaped like what `starkbank.event.parse()` returns,
using SimpleNamespace for attribute-based nested access.
"""

from types import SimpleNamespace

from app.models.invoice import CORRELATION_TAG_PREFIX


def make_invoice_event(log_type, *, stark_id, amount=1000, fee=0, correlation_id=None):
    tags = [f"{CORRELATION_TAG_PREFIX}{correlation_id}"] if correlation_id else []
    invoice = SimpleNamespace(
        id=stark_id,
        amount=amount,
        fee=fee,
        tags=tags,
    )
    log = SimpleNamespace(type=log_type, invoice=invoice)
    return SimpleNamespace(subscription="invoice", log=log)


def make_transfer_event(log_type, *, stark_id, external_id=None, amount=1000):
    transfer = SimpleNamespace(
        id=stark_id,
        amount=amount,
        external_id=external_id,
    )
    log = SimpleNamespace(type=log_type, transfer=transfer)
    return SimpleNamespace(subscription="transfer", log=log)


def make_unknown_event(subscription, log_type):
    return SimpleNamespace(
        subscription=subscription,
        log=SimpleNamespace(type=log_type),
    )
