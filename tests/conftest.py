"""
Test setup.

Important: we substitute `app.db.db` with the test database BEFORE any other
module that does `from app.db import db` is imported. This ensures that any
code calling `db.atomic()` or `db.execute_sql()` operates against the test DB,
not production.
"""

from playhouse.db_url import connect

from app.config import TEST_DATABASE_URL

test_db = connect(TEST_DATABASE_URL)

# Replace the prod db reference at module level. Done before any other app
# imports so that subsequent `from app.db import db` picks up the test_db.
import app.db  # noqa: E402

app.db.db = test_db


# Now safe to import everything else
from types import SimpleNamespace  # noqa: E402
from unittest.mock import MagicMock  # noqa: E402

import pytest  # noqa: E402

from app.huey_app import huey  # noqa: E402
from app.models.api_log import ApiLog  # noqa: E402
from app.models.destination_account import DestinationAccount  # noqa: E402
from app.models.invoice import Invoice  # noqa: E402
from app.models.payer import Payer  # noqa: E402
from app.models.transfer import Transfer  # noqa: E402

MODELS = [ApiLog, DestinationAccount, Payer, Invoice, Transfer]


@pytest.fixture(scope="session", autouse=True)
def _bind_models():
    """Bind all models to the test database for the entire session."""
    test_db.bind(MODELS)
    test_db.connect(reuse_if_open=True)
    test_db.drop_tables(MODELS, safe=True)
    test_db.create_tables(MODELS)
    yield
    test_db.drop_tables(MODELS, safe=True)
    if not test_db.is_closed():
        test_db.close()


@pytest.fixture(autouse=True)
def _truncate_tables():
    """Reset table data between tests (faster than drop/create)."""
    yield
    table_names = ", ".join(f'"{m._meta.table_name}"' for m in MODELS)
    test_db.execute_sql(f"TRUNCATE TABLE {table_names} RESTART IDENTITY CASCADE;")


@pytest.fixture(autouse=True)
def huey_immediate():
    previous = huey.immediate
    huey.immediate = True
    yield
    huey.immediate = previous


@pytest.fixture
def mock_sdk(monkeypatch):
    """
    Mock the StarkBank SDK entry points used across the app:
    - `starkbank.event.parse` (webhook handler)
    - `starkbank.transfer.create` (transfer job/service)
    - `starkbank.invoice.create` (invoice job/service)
    """
    event_parse = MagicMock()
    transfer_create = MagicMock()
    invoice_create = MagicMock()

    import app.services.starkbank_invoice as invoice_service
    import app.services.starkbank_transfer as transfer_service
    import app.services.webhooks.starkbank_webhook_service as webhook_service

    monkeypatch.setattr(webhook_service.starkbank, "event", SimpleNamespace(parse=event_parse))
    monkeypatch.setattr(transfer_service.starkbank, "transfer", SimpleNamespace(create=transfer_create))
    monkeypatch.setattr(invoice_service.starkbank, "invoice", SimpleNamespace(create=invoice_create))

    return SimpleNamespace(
        event_parse=event_parse,
        transfer_create=transfer_create,
        invoice_create=invoice_create,
    )


@pytest.fixture
def app(monkeypatch):
    # Skip StarkBank credential setup in tests
    monkeypatch.setattr("app.flask_app.init_starkbank", lambda: None)
    from app.flask_app import create_app

    app = create_app()
    app.config["TESTING"] = True
    return app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def default_destination_account():
    from tests.factories import DestinationAccountFactory

    return DestinationAccountFactory(default=True)


def post_webhook(client, body=b"{}", signature="fake-signature"):
    return client.post(
        "/webhook",
        data=b"{}" if body is None else body,
        headers={"Digital-Signature": signature},
    )
