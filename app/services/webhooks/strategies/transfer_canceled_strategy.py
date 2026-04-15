import logging

from app.db import db
from app.services.webhooks.strategies._transfer_lookup import find_transfer

logger = logging.getLogger(__name__)


class TransferCanceledStrategy:
    def handle(self, event):
        sb_transfer = event.log.transfer

        transfer = find_transfer(sb_transfer)
        if transfer is None:
            logger.warning(
                f"Transfer with Stark ID {sb_transfer.id} not found locally "
                f"(may have been created outside this app); skipping."
            )
            return

        with db.atomic():
            transfer.mark_as_canceled(stark_id=sb_transfer.id)
            transfer.save()

        logger.warning(
            f"Transfer {transfer.stark_id} was CANCELED "
            f"(local id={transfer.id}, invoice={transfer.invoice_id}, amount={transfer.amount})"
        )
