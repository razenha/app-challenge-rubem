from app.models.transfer import Transfer


def find_transfer(sb_transfer):
    """
    Lookup a Transfer by external_id when available, falling back to stark_id.
    Returns None if not found.

    Using external_id avoids the race condition where the webhook arrives
    before the worker has persisted the stark_id locally.
    """
    external_id = getattr(sb_transfer, "external_id", None)
    if external_id:
        transfer = Transfer.get_or_none(Transfer.external_id == external_id)
        if transfer is not None:
            return transfer

    return Transfer.get_or_none(Transfer.stark_id == sb_transfer.id)
