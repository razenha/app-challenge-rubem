from pydantic import BaseModel
from pydantic_br import CNPJ

from app.models.destination_account import AccountType


class DestinationAccountCreate(BaseModel):
    bank_code: str
    branch: str
    account_number: str
    name: str
    tax_id: CNPJ
    account_type: AccountType
