
from sqlalchemy.orm import Session

from . import models, schemas


class InsufficientStockError(Exception):
    pass


class ProductNotFoundError(Exception):
    pass


class ReservationNotFoundError(Exception):
    pass


class ReservationAlreadyReleasedError(Exception):
    pass


def reserve_product(db: Session, request: schemas.ReserveRequest):

    # Prvo zakljucavamo proizvod
    product = (
        db.query(models.Product)
        .filter(models.Product.id == request.product_id)
        .with_for_update()
        .first()
    )

    if product is None:
        raise ProductNotFoundError("Product not found")

    # Provera da li rezervacija vec postoji
    existing_reservation = (
        db.query(models.Reservation)
        .filter(models.Reservation.saga_id == request.saga_id)
        .first()
    )

    if existing_reservation:
        if existing_reservation.status == "RELEASED":
            raise ReservationAlreadyReleasedError(
                "Reservation already released"
            )

        return {
            "message": "Product already reserved",
            "product_id": existing_reservation.product_id,
            "quantity": existing_reservation.quantity
        }

    if product.quantity < request.quantity:
        raise InsufficientStockError("Not enough stock")

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


def release_product(db: Session, request: schemas.ReleaseRequest):

    # Pronalazimo rezervaciju preko saga_id
    reservation = (
        db.query(models.Reservation)
        .filter(models.Reservation.saga_id == request.saga_id)
        .first()
    )

    if reservation is None:
        raise ReservationNotFoundError("Reservation not found")

    # Zakljucavamo proizvod
    product = (
        db.query(models.Product)
        .filter(models.Product.id == reservation.product_id)
        .with_for_update()
        .first()
    )

    if product is None:
        raise ProductNotFoundError("Product not found")

    # Zakljucavamo rezervaciju i ponovo ucitavamo status
    reservation = (
        db.query(models.Reservation)
        .filter(models.Reservation.saga_id == request.saga_id)
        .populate_existing()
        .with_for_update()
        .first()
    )

    # Idempotentnost
    if reservation.status == "RELEASED":
        return {
            "message": "Product already released",
            "product_id": reservation.product_id
        }

    # Vracamo proizvode
    product.quantity += reservation.quantity

    # Oznacavamo rezervaciju kao oslobodjenu
    reservation.status = "RELEASED"

    db.commit()
    db.refresh(product)

    return {
        "message": "Product released",
        "product_id": product.id,
        "quantity": product.quantity
    }
