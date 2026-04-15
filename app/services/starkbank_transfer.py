import starkbank

from app.db import db
from app.models.destination_account import DestinationAccount
from app.models.invoice import Invoice
from app.models.transfer import Transfer, TransferStatus
from app.services.api_logger import log_outgoing


class StarkBankTransferService:
    def __init__(self, sdk=starkbank):
        self.sdk = sdk

    def send(self, invoice_stark_id, transfer_amount):
        destination = DestinationAccount.get_default()
        invoice = Invoice.get(Invoice.stark_id == invoice_stark_id)

        with db.atomic():
            transfer = Transfer.create(
                invoice=invoice,
                destination_account=destination,
                amount=transfer_amount,
                status=TransferStatus.PENDING.value,
            )

        sb_transfers = self.sdk.transfer.create([
            self.sdk.Transfer(
                amount=transfer_amount,
                bank_code=destination.bank_code,
                branch_code=destination.branch,
                account_number=destination.account_number,
                account_type=destination.account_type,
                name=destination.name,
                tax_id=destination.tax_id,
                external_id=transfer.external_id,
                description=f"Transfering funds from invoice {invoice.stark_id}",
            )
        ])

        sb_transfer = sb_transfers[0]
        stark_id = sb_transfer.id

        self._update_transfer_after_api_call(transfer, stark_id)

        log_outgoing(
            method="POST",
            url="/v2/transfer",
            headers={},
            body={
                "transfers": [{
                    "amount": sb_transfer.amount,
                    "name": destination.name,
                    "tax_id": destination.tax_id,
                    "external_id": transfer.external_id,
                    "description": sb_transfer.description,
                }]
            },
            status_code=200,
        )
        
        return transfer

    def _update_transfer_after_api_call(self, transfer, stark_id):
        with db.atomic():
            transfer = Transfer.select().where(Transfer.id == transfer.id).for_update().get()
            transfer.status = TransferStatus.SENT.value
            transfer.stark_id = stark_id
            transfer.save()