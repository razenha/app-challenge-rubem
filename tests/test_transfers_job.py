"""
Testes de cenários do job de transferência (disparado pelo webhook de invoice/credited).
"""

from types import SimpleNamespace

from app.jobs.transfers import send_transfer
from app.models.transfer import Transfer, TransferStatus
from tests.factories import InvoiceFactory


class TestSendTransferJobScenarios:
    """
    Cenário: depois que uma invoice é creditada, o webhook enfileira este job
    para criar a transferência local e enviá-la ao Stark Bank.
    """

    def test_job_run_creates_transfer_and_sends_it_to_starkbank(
        self, mock_sdk, default_destination_account
    ):
        invoice = InvoiceFactory(amount=10000, stark_id="sb-inv-job-tr")
        mock_sdk.transfer_create.return_value = [
            SimpleNamespace(id="sb-tr-job-1", amount=9850, description="")
        ]

        send_transfer(invoice_stark_id="sb-inv-job-tr", amount=9850)

        # Transfer foi criada localmente e linkada à invoice + conta destino
        transfer = Transfer.get(Transfer.invoice == invoice)
        assert transfer.amount == 9850
        assert transfer.destination_account.id == default_destination_account.id

        # Após a chamada do SDK, a transfer ficou com stark_id e status SENT
        assert transfer.stark_id == "sb-tr-job-1"
        assert transfer.status == TransferStatus.SENT.value

        # SDK foi chamado uma única vez com o payload correto
        mock_sdk.transfer_create.assert_called_once()
        sb_transfer = mock_sdk.transfer_create.call_args[0][0][0]
        assert sb_transfer.amount == 9850
        assert sb_transfer.bank_code == default_destination_account.bank_code
        assert sb_transfer.account_number == default_destination_account.account_number
        assert sb_transfer.tax_id == default_destination_account.tax_id
        assert sb_transfer.external_id == transfer.external_id
