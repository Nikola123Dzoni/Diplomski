
import pytest

from payment_service import models, schemas, service


@pytest.fixture
def account(payment_db):
    account = models.Account(
        client_id=1,
        balance=1000.0
    )

    payment_db.add(account)
    payment_db.commit()
    payment_db.refresh(account)

    return account


@pytest.fixture
def completed_payment(payment_db, account):
    request = schemas.PaymentCreate(
        saga_id=1,
        order_id=1,
        account_id=account.id,
        amount=100.0
    )

    return service.pay(payment_db, request)


# CREATE ACCOUNT

def test_create_account(payment_db):
    request = schemas.AccountCreate(
        client_id=1,
        balance=1000.0
    )

    result = service.create_account(payment_db, request)

    assert result.id is not None
    assert result.client_id == 1
    assert result.balance == 1000.0


# GET ACCOUNTS

def test_get_accounts_empty(payment_db):
    assert service.get_accounts(payment_db) == []


def test_get_accounts(payment_db, account):
    accounts = service.get_accounts(payment_db)

    assert len(accounts) == 1
    assert accounts[0].id == account.id


# GET ACCOUNT

def test_get_account(payment_db, account):
    result = service.get_account(payment_db, account.id)

    assert result.id == account.id
    assert result.balance == 1000.0


def test_get_account_not_found(payment_db):
    with pytest.raises(service.AccountNotFoundError):
        service.get_account(payment_db, 999)


# GET PAYMENTS

def test_get_payments_empty(payment_db):
    assert service.get_payments(payment_db) == []


def test_get_payments(payment_db, completed_payment):
    payments = service.get_payments(payment_db)

    assert len(payments) == 1
    assert payments[0].id == completed_payment.id


# PAY

def test_pay_success(payment_db, account):
    request = schemas.PaymentCreate(
        saga_id=1,
        order_id=1,
        account_id=account.id,
        amount=100.0
    )

    result = service.pay(payment_db, request)

    payment_db.refresh(account)

    assert result.status == "COMPLETED"
    assert result.saga_id == 1
    assert result.order_id == 1
    assert result.amount == 100.0
    assert account.balance == 900.0


def test_pay_idempotent(payment_db, account):
    request = schemas.PaymentCreate(
        saga_id=1,
        order_id=1,
        account_id=account.id,
        amount=100.0
    )

    first = service.pay(payment_db, request)
    second = service.pay(payment_db, request)

    payment_db.refresh(account)

    assert first.id == second.id
    assert account.balance == 900.0
    assert len(service.get_payments(payment_db)) == 1


def test_pay_insufficient_funds(payment_db, account):
    request = schemas.PaymentCreate(
        saga_id=1,
        order_id=1,
        account_id=account.id,
        amount=2000.0
    )

    with pytest.raises(service.InsufficientFundsError):
        service.pay(payment_db, request)

    payment_db.refresh(account)

    assert account.balance == 1000.0
    assert service.get_payments(payment_db) == []


def test_pay_account_not_found(payment_db):
    request = schemas.PaymentCreate(
        saga_id=1,
        order_id=1,
        account_id=999,
        amount=100.0
    )

    with pytest.raises(service.AccountNotFoundError):
        service.pay(payment_db, request)


# REFUND

def test_refund_success(payment_db, account, completed_payment):
    request = schemas.PaymentRefund(saga_id=1)

    result = service.refund_payment(payment_db, request)

    payment_db.refresh(account)

    assert result.status == "REFUNDED"
    assert account.balance == 1000.0


def test_refund_idempotent(payment_db, account, completed_payment):
    request = schemas.PaymentRefund(saga_id=1)

    first = service.refund_payment(payment_db, request)
    second = service.refund_payment(payment_db, request)

    payment_db.refresh(account)

    assert first.id == second.id
    assert second.status == "REFUNDED"
    assert account.balance == 1000.0


def test_refund_payment_not_found(payment_db):
    request = schemas.PaymentRefund(saga_id=999)

    with pytest.raises(service.PaymentNotFoundError):
        service.refund_payment(payment_db, request)


def test_pay_after_refund(payment_db, account, completed_payment):
    service.refund_payment(
        payment_db,
        schemas.PaymentRefund(saga_id=1)
    )

    request = schemas.PaymentCreate(
        saga_id=1,
        order_id=1,
        account_id=account.id,
        amount=100.0
    )

    with pytest.raises(service.PaymentAlreadyRefundedError):
        service.pay(payment_db, request)

    payment_db.refresh(account)

    assert account.balance == 1000.0


# DELETE TEST DATA

def test_delete_test_account_data(payment_db, account, completed_payment):
    deleted_id = service.delete_test_account_data(
        payment_db,
        account.id
    )

    assert deleted_id == account.id
    assert service.get_accounts(payment_db) == []
    assert service.get_payments(payment_db) == []


def test_delete_nonexistent_account_data(payment_db):
    deleted_id = service.delete_test_account_data(
        payment_db,
        999
    )

    assert deleted_id == 999
    assert service.get_accounts(payment_db) == []
