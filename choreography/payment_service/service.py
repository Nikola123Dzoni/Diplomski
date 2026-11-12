
from sqlalchemy.orm import Session

from . import models, schemas


class AccountNotFoundError(Exception):
    pass


class InsufficientFundsError(Exception):
    pass


class PaymentAlreadyRefundedError(Exception):
    pass


def pay(db: Session, payment: schemas.PaymentCreate):
    # Zakljucavamo racun
    account = (
        db.query(models.Account)
        .filter(models.Account.id == payment.account_id)
        .with_for_update()
        .first()
    )

    if account is None:
        raise AccountNotFoundError("Account not found")

    # Proveravamo da li je Saga vec izvrsila placanje
    existing_payment = db.query(models.Payment).filter(
        models.Payment.saga_id == payment.saga_id
    ).first()

    if existing_payment:
        if existing_payment.status == "REFUNDED":
            raise PaymentAlreadyRefundedError(
                "Payment already refunded"
            )

        return existing_payment

    if account.balance < payment.amount:
        raise InsufficientFundsError("Insufficient funds")

    # Skidamo novac
    account.balance -= payment.amount

    # Kreiramo zapis o placanju
    new_payment = models.Payment(
        saga_id=payment.saga_id,
        order_id=payment.order_id,
        account_id=payment.account_id,
        amount=payment.amount,
        status="COMPLETED"
    )

    db.add(new_payment)
    db.commit()
    db.refresh(new_payment)

    return new_payment
