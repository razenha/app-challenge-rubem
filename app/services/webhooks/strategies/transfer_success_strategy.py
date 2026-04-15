import logging

from app.db import db
from app.services.webhooks.strategies._transfer_lookup import find_transfer

logger = logging.getLogger(__name__)


class TransferSuccessStrategy:
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
            transfer.mark_as_success(stark_id=sb_transfer.id)
            transfer.save()

        logger.info(f"Transfer {transfer.stark_id} marked as SUCCESS (local id={transfer.id})")
