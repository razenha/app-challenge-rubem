from typing import Protocol

class WebhookEventStrategy(Protocol):
    def handle(self, event) -> None: ...
