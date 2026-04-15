"""
Testes de cenários do job criação de invoices aleatórias e envio para o Stark Bank.
"""

from types import SimpleNamespace

from app.config import (
    INVOICE_MAX_AMOUNT,
    INVOICE_MAX_COUNT,
    INVOICE_MIN_AMOUNT,
    INVOICE_MIN_COUNT,
)
from app.jobs.invoices import create_invoices
from app.models.invoice import CORRELATION_TAG_PREFIX, Invoice, InvoiceStatus
from tests.factories import PayerFactory


def _fake_sdk_invoice_response(invoices):
    """Espelha a resposta real do SDK: cada Invoice enviada volta com `id` preenchido."""
    return [
        SimpleNamespace(
            id=f"sb-inv-{i}",
            name=inv.name,
            tax_id=inv.tax_id,
            amount=inv.amount,
            tags=inv.tags,
        )
        for i, inv in enumerate(invoices)
    ]


def _seed_payers(count=INVOICE_MAX_COUNT):
    """Garante payers suficientes para o `Payer.select_random(count)` do job."""
    for _ in range(count):
        PayerFactory()


class TestCreateInvoicesJobScenarios:
    """
    Cenário: criação e envio ao Stark Bank invoices aleatórias, entre uma quantidade e valores mínimos e máximos configurados.
    """

    def test_job_run_creates_invoices_and_sends_them_to_starkbank(self, mock_sdk):
        _seed_payers()
        mock_sdk.invoice_create.side_effect = _fake_sdk_invoice_response

        create_invoices()

        invoices = list(Invoice.select())

        # Quantidade dentro do range configurado
        assert INVOICE_MIN_COUNT <= len(invoices) <= INVOICE_MAX_COUNT

        # Cada invoice tem amount dentro do range configurado
        assert all(INVOICE_MIN_AMOUNT <= inv.amount <= INVOICE_MAX_AMOUNT for inv in invoices)

        # Cada invoice ficou com stark_id preenchido e status SENT após a chamada do SDK
        assert all(inv.stark_id is not None for inv in invoices)
        assert all(inv.status == InvoiceStatus.SENT.value for inv in invoices)

        # SDK foi chamado uma única vez com a lista completa
        mock_sdk.invoice_create.assert_called_once()
        sb_invoices_sent = mock_sdk.invoice_create.call_args[0][0]
        assert len(sb_invoices_sent) == len(invoices)

        # Cada invoice enviada carrega o correlation_id local via tag
        local_correlation_ids = {inv.correlation_id for inv in invoices}
        sent_correlation_ids = set()
        for sb_inv in sb_invoices_sent:
            assert len(sb_inv.tags) == 1
            tag = sb_inv.tags[0]
            assert tag.startswith(CORRELATION_TAG_PREFIX)
            sent_correlation_ids.add(tag[len(CORRELATION_TAG_PREFIX):])

        assert sent_correlation_ids == local_correlation_ids
