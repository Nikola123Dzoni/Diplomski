from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

from .database import engine, get_db
from . import models, schemas, service


models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Inventory Service")


@app.get("/")
def root():
    return {"message": "Inventory Service radi"}


@app.post("/products", response_model=schemas.ProductResponse)
def create_product(
    product: schemas.ProductCreate,
    db: Session = Depends(get_db)
):
    return service.create_product(db, product)


@app.get("/products", response_model=list[schemas.ProductResponse])
def get_products(db: Session = Depends(get_db)):
    return service.get_products(db)

@app.get("/reservations", response_model=list[schemas.ReservationResponse])
def get_reservations(db: Session = Depends(get_db)):
    return service.get_reservations(db)



@app.post("/reserve")
def reserve_product(
    request: schemas.ReserveRequest,
    db: Session = Depends(get_db)
):
    try:
        return service.reserve_product(db, request)

    except service.InsufficientStockError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Not enough products in stock"
        )

    except service.ProductNotFoundError:
        db.rollback()
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    except service.ReservationAlreadyReleasedError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Reservation already released"
        )


@app.post("/release")
def release_product(
    request: schemas.ReleaseRequest,
    db: Session = Depends(get_db)
):
    try:
        return service.release_product(db, request)

    except service.ReservationNotFoundError:
        db.rollback()
        raise HTTPException(
            status_code=404,
            detail="Reservation not found"
        )

    except service.ProductNotFoundError:
        db.rollback()
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )


@app.delete("/products/{product_id}")
def delete_product(
    product_id: int,
    db: Session = Depends(get_db)
):
    try:
        deleted_id = service.delete_product(db, product_id)

        return {
            "message": "Product deleted",
            "product_id": deleted_id
        }

    except service.ProductNotFoundError:
        db.rollback()
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

@app.delete("/reservations/{saga_id}")
def delete_reservation(
    saga_id: int,
    db: Session = Depends(get_db)
):
    try:
        deleted_saga_id = service.delete_reservation(db, saga_id)

        return {
            "message": "Reservation deleted",
            "saga_id": deleted_saga_id
        }

    except service.ReservationNotFoundError:
        db.rollback()
        raise HTTPException(
            status_code=404,
            detail="Reservation not found"
        )
