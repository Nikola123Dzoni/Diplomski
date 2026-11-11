from sqlalchemy.orm import Session
from fastapi import HTTPException

from . import models


def update_order_status(db: Session, order_id: int, status: str):
    order = (
        db.query(models.Order)
        .filter(models.Order.id == order_id)
        .with_for_update()
        .first()
    )

    if order is None:
        raise HTTPException(
            status_code=404,
            detail="Order not found"
        )

    if order.status == status:
        db.rollback()
        return order

    if order.status == "CANCELLED":
        raise HTTPException(
            status_code=409,
            detail="Order already cancelled"
        )

    if order.status != "PENDING" or status != "PAID":
        raise HTTPException(
            status_code=409,
            detail="Invalid order status transition"
        )

    order.status = "PAID"

    db.commit()
    db.refresh(order)

    return order