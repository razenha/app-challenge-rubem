"""
Testes de cenários do webhook — focados em comportamento observável, não em implementação.

Cada teste descreve uma situação real do dia-a-dia da app e verifica o efeito final
no sistema (estado dos models, side effects), sem se preocupar com como a engrenagem
funciona por baixo (factory, strategy, lookup, etc).
"""

import logging
from types import SimpleNamespace

from app.models.invoice import Invoice, InvoiceStatus
from app.models.transfer import Transfer, TransferStatus
from tests.conftest import post_webhook
from tests.factories import InvoiceFactory, TransferFactory
from tests.support.fake_events import (
    make_invoice_event,
    make_transfer_event,
    make_unknown_event,
)


# ---------------------------------------------------------------------------
# Cenários: Invoice criada (invoice/created)
# ---------------------------------------------------------------------------


class TestInvoiceCreatedScenarios:
    """
    Cenário: a app envia uma invoice ao Stark Bank e fica esperando
    o webhook de confirmação para marcar a invoice como CREATED.
    """

    def test_recently_sent_invoice_transitions_to_created(
        self, client, mock_sdk
    ):
        invoice = InvoiceFactory(
            status=InvoiceStatus.SENT.value,
            stark_id="sb-inv-001",
        )

        mock_sdk.event_parse.return_value = make_invoice_event(
            "created",
            stark_id="sb-inv-001",
            correlation_id=invoice.correlation_id,
        )
        post_webhook(client)

        invoice = Invoice.get(Invoice.id == invoice.id)
        assert invoice.status == InvoiceStatus.CREATED.value

    def test_webhook_for_invoice_from_another_source_does_not_modify_anything(
        self, client, mock_sdk, caplog
    ):
        invoice = InvoiceFactory(
            status=InvoiceStatus.SENT.value,
            stark_id="sb-inv-002",
        )

        # Webhook vem com correlation_id e stark_id diferentes — simula uma
        # invoice criada por outra integração no mesmo workspace Stark Bank.
        mock_sdk.event_parse.return_value = make_invoice_event(
            "created",
            stark_id="sb-inv-de-outra-app",
            correlation_id="correlation-de-outra-app",
        )
        with caplog.at_level(logging.WARNING):
            post_webhook(client)

        invoice_apos = Invoice.get(Invoice.id == invoice.id)
        assert invoice_apos.status == InvoiceStatus.SENT.value
        assert invoice_apos.stark_id == "sb-inv-002"
        assert any("not found locally" in r.message for r in caplog.records)

    def test_webhook_arrives_before_worker_persists_stark_id(
        self, client, mock_sdk
    ):
        # Race condition real: a app criou a invoice local e enviou ao Stark
        # Bank, mas o webhook respondeu antes do worker conseguir persistir o
        # stark_id no DB. Lookup por correlation_id resolve.
        invoice = InvoiceFactory(
            status=InvoiceStatus.PENDING.value,
            stark_id=None,
        )

        mock_sdk.event_parse.return_value = make_invoice_event(
            "created",
            stark_id="sb-inv-race",
            correlation_id=invoice.correlation_id,
        )
        post_webhook(client)

        invoice = Invoice.get(Invoice.id == invoice.id)
        assert invoice.stark_id == "sb-inv-race"
        assert invoice.status == InvoiceStatus.CREATED.value

    def test_processing_the_same_webhook_twice_is_idempotent(self, client, mock_sdk):
        # Stark Bank reentrega webhooks após timeout. Processar o mesmo evento
        # duas vezes deve produzir o mesmo estado final.
        invoice = InvoiceFactory(
            status=InvoiceStatus.SENT.value,
            stark_id="sb-inv-idem",
        )
        evento = make_invoice_event(
            "created",
            stark_id="sb-inv-idem",
            correlation_id=invoice.correlation_id,
        )
        mock_sdk.event_parse.return_value = evento

        post_webhook(client)
        post_webhook(client)

        invoice = Invoice.get(Invoice.id == invoice.id)
        assert invoice.status == InvoiceStatus.CREATED.value
        assert invoice.stark_id == "sb-inv-idem"


# ---------------------------------------------------------------------------
# Cenários: Invoice creditada (invoice/credited)
# ---------------------------------------------------------------------------


class TestInvoiceCreditedScenarios:
    """
    Cenário: invoice foi paga pelo cliente, o dinheiro caiu na
    conta Stark Bank — agora a app precisa repassar para a conta destino.
    """

    def test_when_invoice_is_credited_app_transfers_amount_to_destination_account(
        self, client, mock_sdk, default_destination_account
    ):
        invoice = InvoiceFactory(
            amount=10000,
            stark_id="sb-inv-c1",
            status=InvoiceStatus.PAID.value,
        )
        mock_sdk.event_parse.return_value = make_invoice_event(
            "credited",
            stark_id="sb-inv-c1",
            amount=10000,
            fee=0,
            correlation_id=invoice.correlation_id,
        )
        mock_sdk.transfer_create.return_value = [
            SimpleNamespace(id="sb-tr-c1", amount=10000, description="")
        ]

        post_webhook(client)

        transfer = Transfer.get(Transfer.invoice == invoice)
        assert transfer.amount == 10000
        assert transfer.destination_account.id == default_destination_account.id

        # Garante que o SDK foi chamado com os dados certos da conta destino
        # e o external_id da transfer local (idempotência)
        mock_sdk.transfer_create.assert_called_once()
        sb_transfer = mock_sdk.transfer_create.call_args[0][0][0]
        assert sb_transfer.amount == 10000
        assert sb_transfer.bank_code == default_destination_account.bank_code
        assert sb_transfer.account_number == default_destination_account.account_number
        assert sb_transfer.tax_id == default_destination_account.tax_id
        assert sb_transfer.external_id == transfer.external_id

    def test_starkbank_fee_is_deducted_from_transfer_amount(
        self, client, mock_sdk, default_destination_account
    ):
        invoice = InvoiceFactory(
            amount=10000,
            stark_id="sb-inv-c2",
            status=InvoiceStatus.PAID.value,
        )
        mock_sdk.event_parse.return_value = make_invoice_event(
            "credited",
            stark_id="sb-inv-c2",
            amount=10000,
            fee=150,
            correlation_id=invoice.correlation_id,
        )
        mock_sdk.transfer_create.return_value = [
            SimpleNamespace(id="sb-tr-c2", amount=9850, description="")
        ]

        post_webhook(client)

        transfer = Transfer.get(Transfer.invoice == invoice)
        assert transfer.amount == 9850

        invoice = Invoice.get(Invoice.id == invoice.id)
        assert invoice.processing_fee == 150

        # Confirma que o SDK foi chamado com o valor já com fee descontado
        # (não com o valor bruto da invoice)
        mock_sdk.transfer_create.assert_called_once()
        sb_transfer = mock_sdk.transfer_create.call_args[0][0][0]
        assert sb_transfer.amount == 9850

    def test_credited_invoice_from_another_source_does_not_trigger_transfer(
        self, client, mock_sdk, default_destination_account, caplog
    ):
        mock_sdk.event_parse.return_value = make_invoice_event(
            "credited",
            stark_id="sb-inv-externa",
            amount=10000,
            fee=0,
            correlation_id="outra-app",
        )
        with caplog.at_level(logging.WARNING):
            post_webhook(client)

        assert Transfer.select().count() == 0
        mock_sdk.transfer_create.assert_not_called()

    def test_created_invoice_can_be_credited_directly_without_paid(
        self, client, mock_sdk, default_destination_account
    ):
        # Em alguns casos o Stark Bank pode emitir o "credited" sem passar
        # pelo "paid" intermediário — o workflow permite essa transição direta.
        invoice = InvoiceFactory(
            amount=10000,
            stark_id="sb-inv-direct",
            status=InvoiceStatus.CREATED.value,
        )
        mock_sdk.event_parse.return_value = make_invoice_event(
            "credited",
            stark_id="sb-inv-direct",
            amount=10000,
            fee=0,
            correlation_id=invoice.correlation_id,
        )
        mock_sdk.transfer_create.return_value = [
            SimpleNamespace(id="sb-tr-direct", amount=10000, description="")
        ]

        post_webhook(client)

        invoice = Invoice.get(Invoice.id == invoice.id)
        assert invoice.status == InvoiceStatus.CREDITED.value
        assert Transfer.select().where(Transfer.invoice == invoice).count() == 1


# ---------------------------------------------------------------------------
# Cenários: Invoice paga (invoice/paid)
# ---------------------------------------------------------------------------


class TestInvoicePaidScenarios:
    """
    Cenário: o Stark Bank confirma que a invoice foi paga pelo
    cliente. Diferente do "credited", o evento "paid" só atualiza o estado
    contábil — a transferência só é disparada quando o dinheiro de fato
    cai na conta (evento "credited").
    """

    def test_paid_invoice_transitions_to_paid_and_records_fee(self, client, mock_sdk):
        invoice = InvoiceFactory(
            amount=10000,
            stark_id="sb-inv-pago",
            status=InvoiceStatus.CREATED.value,
        )

        mock_sdk.event_parse.return_value = make_invoice_event(
            "paid",
            stark_id="sb-inv-pago",
            amount=10000,
            fee=150,
            correlation_id=invoice.correlation_id,
        )
        post_webhook(client)

        invoice = Invoice.get(Invoice.id == invoice.id)
        assert invoice.status == InvoiceStatus.PAID.value
        assert invoice.processing_fee == 150

    def test_paid_invoice_does_not_trigger_transfer(
        self, client, mock_sdk, default_destination_account
    ):
        # "paid" indica que o cliente pagou, mas o dinheiro ainda não está
        # disponível para transferência — isso só acontece no "credited".
        invoice = InvoiceFactory(
            amount=10000,
            stark_id="sb-inv-paid-sem-tr",
            status=InvoiceStatus.CREATED.value,
        )

        mock_sdk.event_parse.return_value = make_invoice_event(
            "paid",
            stark_id="sb-inv-paid-sem-tr",
            amount=10000,
            fee=0,
            correlation_id=invoice.correlation_id,
        )
        post_webhook(client)

        assert Transfer.select().count() == 0
        mock_sdk.transfer_create.assert_not_called()

    def test_paid_webhook_for_invoice_from_another_source_is_ignored(
        self, client, mock_sdk, caplog
    ):
        mock_sdk.event_parse.return_value = make_invoice_event(
            "paid",
            stark_id="sb-inv-externa-paid",
            amount=10000,
            fee=100,
            correlation_id="outra-app-paid",
        )
        with caplog.at_level(logging.WARNING):
            post_webhook(client)

        assert Invoice.select().count() == 0
        assert any("not found locally" in r.message for r in caplog.records)

# ---------------------------------------------------------------------------
# Cenários: Invoice cancelada (invoice/canceled)
# ---------------------------------------------------------------------------


class TestInvoiceCanceledScenarios:
    """
    Cenário: o Stark Bank confirma que uma invoice foi cancelada (ex: o emissor
    cancelou via dashboard ou API antes do pagamento).
    """

    def test_canceled_invoice_transitions_to_canceled(self, client, mock_sdk):
        invoice = InvoiceFactory(
            stark_id="sb-inv-cancel",
            status=InvoiceStatus.CREATED.value,
        )

        mock_sdk.event_parse.return_value = make_invoice_event(
            "canceled",
            stark_id="sb-inv-cancel",
            correlation_id=invoice.correlation_id,
        )
        post_webhook(client)

        invoice = Invoice.get(Invoice.id == invoice.id)
        assert invoice.status == InvoiceStatus.CANCELED.value

    def test_canceled_webhook_for_invoice_from_another_source_is_ignored(
        self, client, mock_sdk, caplog
    ):
        mock_sdk.event_parse.return_value = make_invoice_event(
            "canceled",
            stark_id="sb-inv-cancel-externa",
            correlation_id="outra-app-cancel",
        )
        with caplog.at_level(logging.WARNING):
            post_webhook(client)

        assert Invoice.select().count() == 0
        assert any("not found locally" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# Cenários: Invoice em atraso (invoice/overdue)
# ---------------------------------------------------------------------------


class TestInvoiceOverdueScenarios:
    """
    Cenário: a invoice passou do vencimento sem ser paga. O Stark Bank
    notifica via webhook e a app marca como OVERDUE para monitoramento.
    """

    def test_overdue_invoice_transitions_to_overdue(self, client, mock_sdk):
        invoice = InvoiceFactory(
            stark_id="sb-inv-overdue",
            status=InvoiceStatus.CREATED.value,
        )

        mock_sdk.event_parse.return_value = make_invoice_event(
            "overdue",
            stark_id="sb-inv-overdue",
            correlation_id=invoice.correlation_id,
        )
        post_webhook(client)

        invoice = Invoice.get(Invoice.id == invoice.id)
        assert invoice.status == InvoiceStatus.OVERDUE.value

    def test_overdue_webhook_for_invoice_from_another_source_is_ignored(
        self, client, mock_sdk, caplog
    ):
        mock_sdk.event_parse.return_value = make_invoice_event(
            "overdue",
            stark_id="sb-inv-overdue-externa",
            correlation_id="outra-app-overdue",
        )
        with caplog.at_level(logging.WARNING):
            post_webhook(client)

        assert Invoice.select().count() == 0
        assert any("not found locally" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# Cenários: Invoice expirada (invoice/expired)
# ---------------------------------------------------------------------------


class TestInvoiceExpiredScenarios:
    """
    Cenário: a invoice ficou em OVERDUE por muito tempo e expirou
    definitivamente — estado terminal após o prazo final de pagamento.
    """

    def test_expired_invoice_transitions_to_expired(self, client, mock_sdk):
        invoice = InvoiceFactory(
            stark_id="sb-inv-expired",
            status=InvoiceStatus.OVERDUE.value,
        )

        mock_sdk.event_parse.return_value = make_invoice_event(
            "expired",
            stark_id="sb-inv-expired",
            correlation_id=invoice.correlation_id,
        )
        post_webhook(client)

        invoice = Invoice.get(Invoice.id == invoice.id)
        assert invoice.status == InvoiceStatus.EXPIRED.value


# ---------------------------------------------------------------------------
# Cenários: Ciclo de vida da Transfer (transfer/created → processing → success)
# ---------------------------------------------------------------------------


class TestTransferLifecycleScenarios:
    """
    Cenário: depois que a app dispara uma transfer, ela acompanha
    o ciclo de vida via webhooks até saber se o dinheiro chegou (success) ou
    se algo deu errado (failed/canceled).
    """

    def test_transfer_follows_full_lifecycle_until_success(self, client, mock_sdk):
        transfer = TransferFactory(
            stark_id="sb-tr-life",
            status=TransferStatus.SENT.value,
        )

        mock_sdk.event_parse.return_value = make_transfer_event(
            "created",
            stark_id="sb-tr-life",
            external_id=transfer.external_id,
        )
        post_webhook(client)
        assert Transfer.get(Transfer.id == transfer.id).status == TransferStatus.CREATED.value

        mock_sdk.event_parse.return_value = make_transfer_event(
            "processing",
            stark_id="sb-tr-life",
            external_id=transfer.external_id,
        )
        post_webhook(client)
        assert Transfer.get(Transfer.id == transfer.id).status == TransferStatus.PROCESSING.value

        mock_sdk.event_parse.return_value = make_transfer_event(
            "success",
            stark_id="sb-tr-life",
            external_id=transfer.external_id,
        )
        post_webhook(client)
        assert Transfer.get(Transfer.id == transfer.id).status == TransferStatus.SUCCESS.value

    def test_failed_transfer_emits_warning_log(self, client, mock_sdk, caplog):
        transfer = TransferFactory(
            stark_id="sb-tr-fail",
            status=TransferStatus.SENT.value,
        )

        mock_sdk.event_parse.return_value = make_transfer_event(
            "failed",
            stark_id="sb-tr-fail",
            external_id=transfer.external_id,
        )
        with caplog.at_level(logging.WARNING):
            post_webhook(client)

        assert Transfer.get(Transfer.id == transfer.id).status == TransferStatus.FAILED.value
        assert any(
            r.levelno == logging.WARNING and "FAILED" in r.message
            for r in caplog.records
        )

    def test_canceled_transfer_emits_warning_log(self, client, mock_sdk, caplog):
        transfer = TransferFactory(
            stark_id="sb-tr-cancel",
            status=TransferStatus.SENT.value,
        )

        mock_sdk.event_parse.return_value = make_transfer_event(
            "canceled",
            stark_id="sb-tr-cancel",
            external_id=transfer.external_id,
        )
        with caplog.at_level(logging.WARNING):
            post_webhook(client)

        assert Transfer.get(Transfer.id == transfer.id).status == TransferStatus.CANCELED.value
        assert any(
            r.levelno == logging.WARNING and "CANCELED" in r.message
            for r in caplog.records
        )

    def test_transfer_webhook_for_unknown_external_id_is_ignored(
        self, client, mock_sdk, caplog
    ):
        # Cobre o lookup compartilhado entre todas as strategies de transfer:
        # se nenhuma transfer local case com o external_id do evento, a app
        # apenas registra o warning.
        mock_sdk.event_parse.return_value = make_transfer_event(
            "success",
            stark_id="sb-tr-orfa",
            external_id="external-id-desconhecido",
        )
        with caplog.at_level(logging.WARNING):
            post_webhook(client)

        assert Transfer.select().count() == 0
        assert any("not found locally" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# Cenários: transições de status inválidas
# ---------------------------------------------------------------------------


class TestInvalidStatusTransitionScenarios:
    """
    Cenário: o Stark Bank entrega um webhook que pediria uma transição de
    status que viola o workflow (ex: invoice já creditada recebendo `paid`).
    A app responde 500 com mensagem explicativa em vez de aplicar a mudança
    silenciosamente.
    """

    def test_credited_invoice_receiving_paid_returns_500(self, client, mock_sdk):
        invoice = InvoiceFactory(
            stark_id="sb-inv-credited",
            status=InvoiceStatus.CREDITED.value,
        )

        mock_sdk.event_parse.return_value = make_invoice_event(
            "paid",
            stark_id="sb-inv-credited",
            amount=invoice.amount,
            fee=0,
            correlation_id=invoice.correlation_id,
        )
        response = post_webhook(client)

        assert response.status_code == 500
        assert "Invalid status transition" in response.json["error"]
        assert "'credited' → 'paid'" in response.json["error"]

        # Estado da invoice não foi alterado
        invoice = Invoice.get(Invoice.id == invoice.id)
        assert invoice.status == InvoiceStatus.CREDITED.value

    def test_canceled_invoice_receiving_credited_returns_500(
        self, client, mock_sdk, default_destination_account
    ):
        invoice = InvoiceFactory(
            stark_id="sb-inv-canceled",
            status=InvoiceStatus.CANCELED.value,
        )

        mock_sdk.event_parse.return_value = make_invoice_event(
            "credited",
            stark_id="sb-inv-canceled",
            amount=invoice.amount,
            fee=0,
            correlation_id=invoice.correlation_id,
        )
        response = post_webhook(client)

        assert response.status_code == 500
        assert "'canceled' → 'credited'" in response.json["error"]

        # E nenhuma transferência foi disparada
        mock_sdk.transfer_create.assert_not_called()

    def test_paid_invoice_receiving_canceled_returns_500(self, client, mock_sdk):
        # Uma vez paga, a invoice só pode ir para CREDITED. CANCELED não é
        # permitido porque o cliente já efetuou o pagamento.
        invoice = InvoiceFactory(
            stark_id="sb-inv-paid",
            status=InvoiceStatus.PAID.value,
        )

        mock_sdk.event_parse.return_value = make_invoice_event(
            "canceled",
            stark_id="sb-inv-paid",
            correlation_id=invoice.correlation_id,
        )
        response = post_webhook(client)

        assert response.status_code == 500
        assert "'paid' → 'canceled'" in response.json["error"]

        invoice = Invoice.get(Invoice.id == invoice.id)
        assert invoice.status == InvoiceStatus.PAID.value

    def test_success_transfer_receiving_failed_returns_500(self, client, mock_sdk):
        transfer = TransferFactory(
            stark_id="sb-tr-success",
            status=TransferStatus.SUCCESS.value,
        )

        mock_sdk.event_parse.return_value = make_transfer_event(
            "failed",
            stark_id="sb-tr-success",
            external_id=transfer.external_id,
        )
        response = post_webhook(client)

        assert response.status_code == 500
        assert "'success' → 'failed'" in response.json["error"]

        transfer = Transfer.get(Transfer.id == transfer.id)
        assert transfer.status == TransferStatus.SUCCESS.value


# ---------------------------------------------------------------------------
# Cenários: eventos não mapeados
# ---------------------------------------------------------------------------


class TestUnknownEventsScenarios:
    """
    Cenário: Evento não mapeado deposit/credited
    """

    def test_app_responds_200_and_logs_unknown_subscription_event(
        self, client, mock_sdk, caplog
    ):
        # Resposta 200 mesmo para evento desconhecido evita reentrega do webhook
        # pelo Stark Bank. O warning fica para alguém investigar e mapear depois.
        mock_sdk.event_parse.return_value = make_unknown_event("deposit", "credited")

        with caplog.at_level(logging.WARNING):
            response = post_webhook(client)

        assert response.status_code == 200
        assert any("Unmapped webhook event" in r.message for r in caplog.records)

    def test_app_handles_new_log_type_on_known_subscription(
        self, client, mock_sdk, caplog
    ):
        mock_sdk.event_parse.return_value = make_unknown_event("invoice", "reversed")

        with caplog.at_level(logging.WARNING):
            response = post_webhook(client)

        assert response.status_code == 200
        assert any(
            "Unmapped webhook event" in r.message and "reversed" in r.message
            for r in caplog.records
        )