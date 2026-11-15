from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from .database import engine, get_db
from . import models, schemas, service
from .rabbitmq import publish_event


models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Order Service")


@app.get("/")
def root():
    return {"message": "Order Service radi"}



@app.post("/create", response_model=schemas.OrderResponse)
def create_order(
    order: schemas.OrderCreate,
    db: Session = Depends(get_db)
):
    new_order, created = service.create_order(db, order)

    if created:
        publish_event("OrderCreated", {
            "saga_id": new_order.saga_id,
            "order_id": new_order.id,
            "product_id": new_order.product_id,
            "account_id": new_order.account_id,
            "quantity": new_order.quantity,
            "amount": new_order.price * new_order.quantity
        })

    return new_order



@app.get("/orders", response_model=list[schemas.OrderResponse])
def get_orders(
    db: Session = Depends(get_db)
):
    return service.get_orders(db)

@app.put("/orders/status", response_model=schemas.OrderResponse)
def update_order_status(
    order_update: schemas.OrderUpdate,
    db: Session = Depends(get_db)
):
    try:
        return service.update_order_status(
            db,
            order_update.id,
            order_update.saga_id,
            order_update.status
        )

    except service.OrderNotFoundError:
        db.rollback()
        raise HTTPException(
            status_code=404,
            detail="Order not found"
        )

    except service.InvalidOrderStatusError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Invalid order status transition"
        )



@app.post("/cancel", response_model=schemas.OrderResponse)
def cancel_order(
    request: schemas.CancelOrderRequest,
    db: Session = Depends(get_db)
):
    try:
        return service.cancel_order(
            db,
            request.order_id,
            request.saga_id
        )

    except service.OrderNotFoundError:
        db.rollback()
        raise HTTPException(
            status_code=404,
            detail="Order not found"
        )

    except service.InvalidOrderStatusError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Order cannot be cancelled"
        )


@app.delete("/test-data/order/{order_id}")
def delete_test_order(
    order_id: int,
    db: Session = Depends(get_db)
):
    order = db.query(models.Order).filter(
        models.Order.id == order_id
    ).first()

    if order is None:
        raise HTTPException(
            status_code=404,
            detail="Order not found"
        )

    db.delete(order)
    db.commit()

    return {
        "message": "Test order deleted",
        "order_id": order_id
    }