
import logging

from app.huey_app import huey
from app.services.starkbank_transfer import StarkBankTransferService

logger = logging.getLogger(__name__)

@huey.task(retries=3, retry_delay=10)
def send_transfer(invoice_stark_id, amount):
    service = StarkBankTransferService()
    service.send(invoice_stark_id, amount)

    logger.info(f"Scheduled transfer to default DestinationAccount for invoice {invoice_stark_id} with amount {amount}.")
