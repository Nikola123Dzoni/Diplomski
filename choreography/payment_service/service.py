
from sqlalchemy.orm import Session

from . import models, schemas


class AccountNotFoundError(Exception):
    pass


class PaymentNotFoundError(Exception):
    pass


class InsufficientFundsError(Exception):
    pass


class PaymentAlreadyRefundedError(Exception):
    pass


# CREATE ACCOUNT

def create_account(db: Session, account: schemas.AccountCreate):
    new_account = models.Account(
        client_id=account.client_id,
        balance=account.balance
    )

    db.add(new_account)
    db.commit()
    db.refresh(new_account)

    return new_account


# GET ACCOUNTS

def get_accounts(db: Session):
    return db.query(models.Account).all()


# GET ACCOUNT

def get_account(db: Session, account_id: int):
    account = (
        db.query(models.Account)
        .filter(models.Account.id == account_id)
        .first()
    )

    if account is None:
        raise AccountNotFoundError("Account not found")

    return account


# GET PAYMENTS

def get_payments(db: Session):
    return db.query(models.Payment).all()


# PAY

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
    existing_payment = (
        db.query(models.Payment)
        .filter(models.Payment.saga_id == payment.saga_id)
        .first()
    )

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


# REFUND

def refund_payment(db: Session, request: schemas.PaymentRefund):

    # Pronalazimo placanje
    payment = (
        db.query(models.Payment)
        .filter(models.Payment.saga_id == request.saga_id)
        .first()
    )

    if payment is None:
        raise PaymentNotFoundError("Payment not found")

    # Zakljucavamo racun
    account = (
        db.query(models.Account)
        .filter(models.Account.id == payment.account_id)
        .with_for_update()
        .first()
    )

    if account is None:
        raise AccountNotFoundError("Account not found")

    # Zakljucavamo placanje i ponovo ucitavamo status
    payment = (
        db.query(models.Payment)
        .filter(models.Payment.saga_id == request.saga_id)
        .populate_existing()
        .with_for_update()
        .first()
    )

    # Idempotentnost
    if payment.status == "REFUNDED":
        return payment

    # Vracamo novac
    account.balance += payment.amount

    payment.status = "REFUNDED"

    db.commit()
    db.refresh(payment)

    return payment


# DELETE TEST DATA

def delete_test_account_data(db: Session, account_id: int):

    # Brisemo sva placanja vezana za racun
    db.query(models.Payment).filter(
        models.Payment.account_id == account_id
    ).delete(synchronize_session=False)

    # Brisemo racun
    account = (
        db.query(models.Account)
        .filter(models.Account.id == account_id)
        .first()
    )

    if account is not None:
        db.delete(account)

    db.commit()

    return account_id
