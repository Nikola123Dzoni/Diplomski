
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

from .database import engine, get_db
from . import models, schemas, service


models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Payment Service")


@app.get("/")
def root():
    return {"message": "Payment Service radi"}


# CREATE ACCOUNT

@app.post("/accounts", response_model=schemas.AccountResponse)
def create_account(
    account: schemas.AccountCreate,
    db: Session = Depends(get_db)
):
    return service.create_account(db, account)


# GET ACCOUNTS

@app.get("/accounts", response_model=list[schemas.AccountResponse])
def get_accounts(db: Session = Depends(get_db)):
    return service.get_accounts(db)


# GET ACCOUNT

@app.get("/accounts/{account_id}", response_model=schemas.AccountResponse)
def get_account(
    account_id: int,
    db: Session = Depends(get_db)
):
    try:
        return service.get_account(db, account_id)

    except service.AccountNotFoundError:
        db.rollback()
        raise HTTPException(
            status_code=404,
            detail="Account not found"
        )


# PAY

@app.post("/pay", response_model=schemas.PaymentResponse)
def create_payment(
    payment: schemas.PaymentCreate,
    db: Session = Depends(get_db)
):
    try:
        return service.pay(db, payment)

    except service.AccountNotFoundError:
        db.rollback()
        raise HTTPException(
            status_code=404,
            detail="Account not found"
        )

    except service.InsufficientFundsError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Insufficient funds"
        )

    except service.PaymentAlreadyRefundedError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Payment already refunded"
        )


# GET PAYMENTS

@app.get("/payments", response_model=list[schemas.PaymentResponse])
def get_payments(db: Session = Depends(get_db)):
    return service.get_payments(db)


# REFUND

@app.post("/refund", response_model=schemas.PaymentResponse)
def refund_payment(
    request: schemas.PaymentRefund,
    db: Session = Depends(get_db)
):
    try:
        return service.refund_payment(db, request)

    except service.PaymentNotFoundError:
        db.rollback()
        raise HTTPException(
            status_code=404,
            detail="Payment not found"
        )

    except service.AccountNotFoundError:
        db.rollback()
        raise HTTPException(
            status_code=404,
            detail="Account not found"
        )


# DELETE TEST DATA

@app.delete("/test-data/account/{account_id}")
def delete_test_account_data(
    account_id: int,
    db: Session = Depends(get_db)
):
    deleted_account_id = service.delete_test_account_data(
        db, account_id
    )

    return {
        "message": "Test data deleted",
        "account_id": deleted_account_id
    }
