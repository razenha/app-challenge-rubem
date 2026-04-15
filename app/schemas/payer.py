from typing import Annotated, Union

from pydantic import BaseModel, EmailStr, field_validator
from pydantic_br import CPF, CNPJ

from app.models.payer import PayerKind


class PayerCreate(BaseModel):
    name: str
    document: Union[CPF, CNPJ]
    email: EmailStr | None = None
    whatsapp: str | None = None
    kind: PayerKind

    @field_validator("whatsapp")
    @classmethod
    def validate_whatsapp(cls, v):
        if v is None:
            return v
        digits = "".join(c for c in v if c.isdigit())
        if len(digits) < 10 or len(digits) > 13:
            raise ValueError("Whatsapp must have 10-13 digits (with country code)")
        return v
