
from fastapi import HTTPException
from sqlalchemy.orm import Session

from . import models, schemas


def reserve_product(db: Session, request: schemas.ReserveRequest):

    # Prvo zakljucavamo proizvod
    product = (
        db.query(models.Product)
        .filter(models.Product.id == request.product_id)
        .with_for_update()
        .first()
    )

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    # Provera da li rezervacija vec postoji
    existing_reservation = (
        db.query(models.Reservation)
        .filter(models.Reservation.saga_id == request.saga_id)
        .first()
    )

    if existing_reservation:
        if existing_reservation.status == "RELEASED":
            raise HTTPException(
                status_code=409,
                detail="Reservation already released"
            )

        return {
            "message": "Product already reserved",
            "product_id": existing_reservation.product_id,
            "quantity": existing_reservation.quantity
        }

    if product.quantity < request.quantity:
        raise HTTPException(
            status_code=400,
            detail="Not enough products in stock"
        )

    product.quantity -= request.quantity

    reservation = models.Reservation(
        saga_id=request.saga_id,
        product_id=request.product_id,
        quantity=request.quantity,
        status="RESERVED"
    )

    db.add(reservation)
    db.commit()
    db.refresh(product)

    return {
        "message": "Product reserved",
        "product_id": product.id,
        "remaining_quantity": product.quantity
    }
