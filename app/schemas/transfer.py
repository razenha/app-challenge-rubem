from pydantic import BaseModel, field_validator


class TransferCreate(BaseModel):
    invoice_id: int
    destination_account_id: int
    amount: int

    @field_validator("amount")
    @classmethod
    def amount_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError("Transfer amount must be positive")
        return v
