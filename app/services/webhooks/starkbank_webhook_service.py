import starkbank

from app.services.api_logger import log_incoming
from app.services.webhooks.starkbank_webhook_event_factory import StarkbankWebhookEventFactory


class StarkbankWebhookService:
    def __init__(self, sdk=starkbank):
        self.sdk = sdk

    def handle(self, method, url, headers, body):
        log_incoming(
            method=method,
            url=url,
            headers=headers,
            body=body,
            status_code=200,
        )

        signature = headers.get("Digital-Signature")
        event = self.sdk.event.parse(
            content=body,
            signature=signature,
        )

        strategy = StarkbankWebhookEventFactory.create(
            event.subscription, event.log.type
        )
        strategy.handle(event)
