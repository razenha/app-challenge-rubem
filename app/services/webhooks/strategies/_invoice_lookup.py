from app.models.invoice import CORRELATION_TAG_PREFIX, Invoice


def find_invoice(sb_invoice):
    """
    Lookup an Invoice by correlation_id (extracted from tags) when available,
    falling back to stark_id. Returns None if not found.

    Using correlation_id avoids the race condition where the webhook arrives
    before the worker has persisted the stark_id locally.
    """
    correlation_id = extract_correlation_id(sb_invoice)
    if correlation_id:
        invoice = Invoice.get_or_none(Invoice.correlation_id == correlation_id)
        if invoice is not None:
            return invoice

    return Invoice.get_or_none(Invoice.stark_id == sb_invoice.id)


def extract_correlation_id(sb_invoice):
    tags = getattr(sb_invoice, "tags", None) or []
    for tag in tags:
        if tag.startswith(CORRELATION_TAG_PREFIX):
            return tag[len(CORRELATION_TAG_PREFIX):]
    return None
