import random
import logging


from huey import crontab

from app.config import (
    INVOICE_MAX_AMOUNT,
    INVOICE_MAX_COUNT,
    INVOICE_MIN_AMOUNT,
    INVOICE_MIN_COUNT,
    INVOICE_SCHEDULE_CRON,
)
from app.db import db
from app.huey_app import huey
from app.models.invoice import Invoice, InvoiceStatus
from app.models.payer import Payer
from app.services.starkbank_invoice import StarkBankInvoiceService


logger = logging.getLogger(__name__)

def create_random_invoices():
    count = random.randint(INVOICE_MIN_COUNT, INVOICE_MAX_COUNT)
    selected_payers = Payer.select_random(count)

    invoices = []
    for payer in selected_payers:
        invoice = Invoice.create(
            payer=payer,
            status=InvoiceStatus.PENDING.value,
            amount=random.randint(INVOICE_MIN_AMOUNT, INVOICE_MAX_AMOUNT),
        )
        invoices.append(invoice)

    return invoices


def _parse_cron(expr):
    minute, hour, day, month, day_of_week = expr.split()
    return crontab(
        minute=minute,
        hour=hour,
        day=day,
        month=month,
        day_of_week=day_of_week,
    )


@huey.periodic_task(_parse_cron(INVOICE_SCHEDULE_CRON))
def create_invoices():
    with db.atomic():
        invoices = create_random_invoices()
        service = StarkBankInvoiceService()
        service.send(invoices)

        logger.info(f"Created and sent {len(invoices)} invoices.")

        return len(invoices)

