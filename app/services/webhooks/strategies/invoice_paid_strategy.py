import logging

from app.db import db
from app.services.webhooks.strategies._invoice_lookup import extract_correlation_id, find_invoice

logger = logging.getLogger(__name__)


class InvoicePaidStrategy:
    def handle(self, event):
        sb_invoice = event.log.invoice

        invoice = find_invoice(sb_invoice)
        if invoice is None:
            logger.warning(
                f"Invoice not found locally "
                f"(stark_id={sb_invoice.id}, correlation_id={extract_correlation_id(sb_invoice)}); "
                f"may have been created outside this app; skipping."
            )
            return

        with db.atomic():
            invoice.mark_as_paid(stark_id=sb_invoice.id, processing_fee=sb_invoice.fee)
            invoice.save()

        logger.info(
            f"Invoice {invoice.stark_id} marked as PAID "
            f"(amount={invoice.amount}, processing_fee={invoice.processing_fee})"
        )
