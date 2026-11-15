
import pytest

from order_service import models, schemas, service


@pytest.fixture
def order(order_db):
    new_order = models.Order(
        saga_id=1,
        product_id=1,
        account_id=1,
        quantity=2,
        price=50.0,
        status="PENDING"
    )

    order_db.add(new_order)
    order_db.commit()
    order_db.refresh(new_order)

    return new_order


# CREATE ORDER

def test_create_order(order_db):
    request = schemas.OrderCreate(
        saga_id=1,
        product_id=1,
        account_id=1,
        quantity=2,
        price=50.0
    )

    result, created = service.create_order(order_db, request)

    assert created is True
    assert result.saga_id == 1
    assert result.status == "PENDING"
    assert result.quantity == 2


def test_create_order_idempotent(order_db):
    request = schemas.OrderCreate(
        saga_id=1,
        product_id=1,
        account_id=1,
        quantity=2,
        price=50.0
    )

    first, created1 = service.create_order(order_db, request)
    second, created2 = service.create_order(order_db, request)

    assert created1 is True
    assert created2 is False
    assert first.id == second.id
    assert order_db.query(models.Order).count() == 1


# GET ORDERS

def test_get_orders_empty(order_db):
    orders = service.get_orders(order_db)

    assert len(orders) == 0


def test_get_orders(order_db, order):
    orders = service.get_orders(order_db)

    assert len(orders) == 1
    assert orders[0].id == order.id


# UPDATE ORDER STATUS

def test_update_order_status(order_db, order):
    result = service.update_order_status(
        order_db, order.id, order.saga_id, "PAID"
    )

    assert result.status == "PAID"


def test_update_order_idempotent(order_db, order):
    service.update_order_status(
        order_db, order.id, order.saga_id, "PAID"
    )

    result = service.update_order_status(
        order_db, order.id, order.saga_id, "PAID"
    )

    assert result.status == "PAID"


def test_update_wrong_saga(order_db, order):
    with pytest.raises(service.OrderNotFoundError):
        service.update_order_status(
            order_db, order.id, 999, "PAID"
        )

    order_db.rollback()
    order_db.refresh(order)

    assert order.status == "PENDING"


def test_update_nonexistent_order(order_db):
    with pytest.raises(service.OrderNotFoundError):
        service.update_order_status(
            order_db, 999, 1, "PAID"
        )

    order_db.rollback()


def test_update_cancelled_order(order_db, order):
    service.cancel_order(
        order_db, order.id, order.saga_id
    )

    with pytest.raises(service.InvalidOrderStatusError):
        service.update_order_status(
            order_db, order.id, order.saga_id, "PAID"
        )

    order_db.rollback()
    order_db.refresh(order)

    assert order.status == "CANCELLED"


def test_update_invalid_status(order_db, order):
    with pytest.raises(service.InvalidOrderStatusError):
        service.update_order_status(
            order_db, order.id, order.saga_id, "FAILED"
        )

    order_db.rollback()
    order_db.refresh(order)

    assert order.status == "PENDING"


# CANCEL ORDER

def test_cancel_order(order_db, order):
    result = service.cancel_order(
        order_db, order.id, order.saga_id
    )

    assert result.status == "CANCELLED"


def test_cancel_idempotent(order_db, order):
    service.cancel_order(
        order_db, order.id, order.saga_id
    )

    result = service.cancel_order(
        order_db, order.id, order.saga_id
    )

    assert result.status == "CANCELLED"


def test_cancel_wrong_saga(order_db, order):
    with pytest.raises(service.OrderNotFoundError):
        service.cancel_order(
            order_db, order.id, 999
        )

    order_db.rollback()
    order_db.refresh(order)

    assert order.status == "PENDING"


def test_cancel_paid_order(order_db, order):
    service.update_order_status(
        order_db, order.id, order.saga_id, "PAID"
    )

    with pytest.raises(service.InvalidOrderStatusError):
        service.cancel_order(
            order_db, order.id, order.saga_id
        )

    order_db.rollback()
    order_db.refresh(order)

    assert order.status == "PAID"


def test_cancel_nonexistent_order(order_db):
    with pytest.raises(service.OrderNotFoundError):
        service.cancel_order(
            order_db, 999, 1
        )

    order_db.rollback()
