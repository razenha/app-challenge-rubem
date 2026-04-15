import starkbank

from app.db import db
from app.models.invoice import CORRELATION_TAG_PREFIX, InvoiceStatus
from app.services.api_logger import log_outgoing


class StarkBankInvoiceService:
    def __init__(self, sdk=starkbank):
        self.sdk = sdk

    def send(self, invoices):
        sb_invoices = [
            self.sdk.Invoice(
                amount=inv.amount,
                name=inv.payer.name,
                tax_id=inv.payer.document,
                tags=[f"{CORRELATION_TAG_PREFIX}{inv.correlation_id}"],
            )
            for inv in invoices
        ]

        api_invoices = self.sdk.invoice.create(sb_invoices)

        log_outgoing(
            method="POST",
            url="/v2/invoice",
            headers={},
            body={"invoices": [
                {"name": i.name, "tax_id": i.tax_id, "amount": i.amount, "tags": i.tags}
                for i in api_invoices
            ]},
            status_code=200,
        )

        with db.atomic():
            for inv, sb_inv in zip(invoices, api_invoices):
                inv.stark_id = sb_inv.id
                inv.status = InvoiceStatus.SENT.value
                inv.save()

        return invoices
