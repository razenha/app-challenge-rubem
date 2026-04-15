import logging

logger = logging.getLogger(__name__)


class UnknownEventStrategy:
    def __init__(self, subscription, log_type):
        self.subscription = subscription
        self.log_type = log_type

    def handle(self, event):
        logger.warning(f"Unmapped webhook event: {self.subscription}/{self.log_type}")
