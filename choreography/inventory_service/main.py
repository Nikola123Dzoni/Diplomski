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
    new_product = models.Product(
        name=product.name,
        quantity=product.quantity
    )

    db.add(new_product)
    db.commit()
    db.refresh(new_product)

    return new_product


@app.get("/products", response_model=list[schemas.ProductResponse])
def get_products(db: Session = Depends(get_db)):
    return db.query(models.Product).all()

@app.get("/reservations", response_model=list[schemas.ReservationResponse])
def get_reservations(db: Session = Depends(get_db)):
    return db.query(models.Reservation).all()



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
    product = db.query(models.Product).filter(
        models.Product.id == product_id
    ).first()

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    db.delete(product)
    db.commit()

    return {
        "message": "Product deleted",
        "product_id": product_id
    }

@app.delete("/reservations/{saga_id}")
def delete_reservation(
    saga_id: int,
    db: Session = Depends(get_db)
):
    reservation = db.query(models.Reservation).filter(
        models.Reservation.saga_id == saga_id
    ).first()

    if reservation is None:
        raise HTTPException(
            status_code=404,
            detail="Reservation not found"
        )

    db.delete(reservation)
    db.commit()

    return {
        "message": "Reservation deleted",
        "saga_id": saga_id
    }

@app.delete("/test-data/product/{product_id}")
def delete_test_product_data(
    product_id: int,
    db: Session = Depends(get_db)
):
    # Brisemo sve rezervacije koje pripadaju ovom proizvodu
    db.query(models.Reservation).filter(
        models.Reservation.product_id == product_id
    ).delete(synchronize_session=False)

    # Pronalazimo proizvod
    product = db.query(models.Product).filter(
        models.Product.id == product_id
    ).first()

    # Brisemo proizvod ako postoji
    if product is not None:
        db.delete(product)

    db.commit()

    return {
        "message": "Test data deleted",
        "product_id": product_id
    }