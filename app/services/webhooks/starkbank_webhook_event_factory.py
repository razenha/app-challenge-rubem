from app.services.webhooks.strategies.invoice_canceled_strategy import InvoiceCanceledStrategy
from app.services.webhooks.strategies.invoice_created_strategy import InvoiceCreatedStrategy
from app.services.webhooks.strategies.invoice_credited_strategy import InvoiceCreditedStrategy
from app.services.webhooks.strategies.invoice_expired_strategy import InvoiceExpiredStrategy
from app.services.webhooks.strategies.invoice_overdue_strategy import InvoiceOverdueStrategy
from app.services.webhooks.strategies.invoice_paid_strategy import InvoicePaidStrategy
from app.services.webhooks.strategies.transfer_canceled_strategy import TransferCanceledStrategy
from app.services.webhooks.strategies.transfer_created_strategy import TransferCreatedStrategy
from app.services.webhooks.strategies.transfer_failed_strategy import TransferFailedStrategy
from app.services.webhooks.strategies.transfer_processing_strategy import TransferProcessingStrategy
from app.services.webhooks.strategies.transfer_success_strategy import TransferSuccessStrategy
from app.services.webhooks.strategies.unknown_event_strategy import UnknownEventStrategy

STRATEGIES = {
    ("invoice", "created"): InvoiceCreatedStrategy,
    ("invoice", "credited"): InvoiceCreditedStrategy,
    ("invoice", "paid"): InvoicePaidStrategy,
    ("invoice", "canceled"): InvoiceCanceledStrategy,
    ("invoice", "overdue"): InvoiceOverdueStrategy,
    ("invoice", "expired"): InvoiceExpiredStrategy,
    ("transfer", "created"): TransferCreatedStrategy,
    ("transfer", "processing"): TransferProcessingStrategy,
    ("transfer", "success"): TransferSuccessStrategy,
    ("transfer", "canceled"): TransferCanceledStrategy,
    ("transfer", "failed"): TransferFailedStrategy,
}


class StarkbankWebhookEventFactory:
    @staticmethod
    def create(subscription, log_type):
        strategy_class = STRATEGIES.get((subscription, log_type))
        if strategy_class is None:
            return UnknownEventStrategy(subscription, log_type)
        return strategy_class()
