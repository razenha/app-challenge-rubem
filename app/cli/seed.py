from faker import Faker

from app.db import db
from app.models.destination_account import DestinationAccount
from app.models.payer import Payer, PayerKind

fake = Faker("pt_BR")


def seed_destination_account():
    DestinationAccount.create(
        bank_code="20018183",
        branch="0001",
        account_number="6341320293482496",
        name="Stark Bank S.A.",
        tax_id="20.018.183/0001-80",
        account_type="payment",
        default=True,
    )
    print("Destination account created.")


def seed_payers():
    payers = []

    for _ in range(20):
        payers.append(
            Payer(
                name=fake.name(),
                document=fake.cpf(),
                email=fake.email(),
                whatsapp=fake.phone_number(),
                kind=PayerKind.INDIVIDUAL.value,
            )
        )

    for _ in range(20):
        payers.append(
            Payer(
                name=fake.company(),
                document=fake.cnpj(),
                email=fake.company_email(),
                whatsapp=fake.phone_number(),
                kind=PayerKind.BUSINESS.value,
            )
        )

    Payer.bulk_create(payers)
    print(f"{len(payers)} payers created (20 individual + 20 business).")


def run():
    db.connect()

    seed_destination_account()
    seed_payers()

    db.close()
    print("Seed complete.")


if __name__ == "__main__":
    run()
