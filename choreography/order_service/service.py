
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from . import models


class OrderNotFoundError(Exception):
    pass


class InvalidOrderStatusError(Exception):
    pass


def create_order(db: Session, order):
    # Proveravamo da li Saga vec ima porudzbinu
    existing_order = (
        db.query(models.Order)
        .filter(models.Order.saga_id == order.saga_id)
        .first()
    )

    if existing_order:
        return existing_order, False

    # Kreiramo novu porudzbinu
    new_order = models.Order(
        saga_id=order.saga_id,
        product_id=order.product_id,
        account_id=order.account_id,
        quantity=order.quantity,
        price=order.price,
        status="PENDING"
    )

    db.add(new_order)

    try:
        db.commit()

    except IntegrityError:
        db.rollback()

        existing_order = (
            db.query(models.Order)
            .filter(models.Order.saga_id == order.saga_id)
            .first()
        )

        if existing_order:
            return existing_order, False

        raise

    db.refresh(new_order)

    return new_order, True

def get_orders(db: Session):
    return db.query(models.Order).all()

def update_order_status(
    db: Session,
    order_id: int,
    saga_id: int,
    status: str
):
    order = (
        db.query(models.Order)
        .filter(
            models.Order.id == order_id,
            models.Order.saga_id == saga_id
        )
        .with_for_update()
        .first()
    )

    if order is None:
        raise OrderNotFoundError("Order not found")

    # Idempotentnost
    if order.status == status:
        db.commit()
        db.refresh(order)
        return order

    if order.status == "CANCELLED":
        raise InvalidOrderStatusError("Order already cancelled")

    if order.status != "PENDING" or status != "PAID":
        raise InvalidOrderStatusError(
            "Invalid order status transition"
        )

    order.status = "PAID"

    db.commit()
    db.refresh(order)

    return order


def cancel_order(db: Session, order_id: int, saga_id: int):
    order = (
        db.query(models.Order)
        .filter(
            models.Order.id == order_id,
            models.Order.saga_id == saga_id
        )
        .with_for_update()
        .first()
    )

    if order is None:
        raise OrderNotFoundError("Order not found")

    # Idempotentna kompenzacija
    if order.status == "CANCELLED":
        db.commit()
        db.refresh(order)
        return order

    if order.status != "PENDING":
        raise InvalidOrderStatusError(
            "Order cannot be cancelled"
        )

    order.status = "CANCELLED"

    db.commit()
    db.refresh(order)

    return order
