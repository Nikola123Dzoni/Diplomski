
from sqlalchemy.orm import Session

from . import models


class OrderNotFoundError(Exception):
    pass


class InvalidOrderStatusError(Exception):
    pass


def update_order_status(db: Session, order_id: int, status: str):
    order = (
        db.query(models.Order)
        .filter(models.Order.id == order_id)
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


def cancel_order(db: Session, order_id: int):
    order = (
        db.query(models.Order)
        .filter(models.Order.id == order_id)
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
