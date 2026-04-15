from pydantic import BaseModel, field_validator


class InvoiceCreate(BaseModel):
    payer_id: int
    amount: int

    @field_validator("amount")
    @classmethod
    def amount_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError("Amount must be positive")
        return v
