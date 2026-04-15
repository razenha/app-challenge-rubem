import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

STARKBANK_ENVIRONMENT = os.getenv("STARKBANK_ENVIRONMENT", "sandbox")
STARKBANK_PROJECT_ID = os.getenv("STARKBANK_PROJECT_ID", "")
STARKBANK_PRIVATE_KEY_PATH = os.getenv("STARKBANK_PRIVATE_KEY_PATH", "./private-key.pem")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///db.sqlite3")
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/starkbank_challenge_test",
)

INVOICE_MIN_COUNT = int(os.getenv("INVOICE_MIN_COUNT", "8"))
INVOICE_MAX_COUNT = int(os.getenv("INVOICE_MAX_COUNT", "12"))
INVOICE_MIN_AMOUNT = int(os.getenv("INVOICE_MIN_AMOUNT", "1000"))
INVOICE_MAX_AMOUNT = int(os.getenv("INVOICE_MAX_AMOUNT", "100000"))

INVOICE_SCHEDULE_CRON = os.getenv("INVOICE_SCHEDULE_CRON", "0 */3 * * *")

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
DEBUG = os.getenv("FLASK_DEBUG", "0") == "1"


def get_private_key():
    path = Path(STARKBANK_PRIVATE_KEY_PATH)
    return path.read_text()
