import logging

from flask import Blueprint, jsonify, request

from app.models.exceptions import InvalidStatusTransitionError
from app.services.webhooks.starkbank_webhook_service import StarkbankWebhookService

logger = logging.getLogger(__name__)

webhook_bp = Blueprint("webhook", __name__)


@webhook_bp.route("/webhook", methods=["POST"])
def handle_webhook():
    content = request.data.decode("utf-8")

    handler = StarkbankWebhookService()
    handler.handle(
        method=request.method,
        url=request.path,
        headers=request.headers,
        body=content,
    )

    return jsonify({"ok": True}), 200


@webhook_bp.app_errorhandler(InvalidStatusTransitionError)
def _handle_invalid_transition(exc):
    # Retorna 500 com a mensagem para o Stark Bank tentar reentregar o webhook
    # depois (ou sinalizar para o time investigar o desalinhamento de estado).
    logger.error(str(exc))
    return jsonify({"error": str(exc)}), 500
