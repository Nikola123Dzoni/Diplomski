
import pytest

from inventory_service import models, schemas, service


@pytest.fixture
def product(inventory_db):
    product = models.Product(
        name="Laptop",
        quantity=10
    )

    inventory_db.add(product)
    inventory_db.commit()
    inventory_db.refresh(product)

    return product


# CREATE PRODUCT

def test_create_product(inventory_db):
    request = schemas.ProductCreate(
        name="Laptop",
        quantity=10
    )

    product = service.create_product(inventory_db, request)

    assert product.id is not None
    assert product.name == "Laptop"
    assert product.quantity == 10


# GET PRODUCTS

def test_get_products_empty(inventory_db):
    products = service.get_products(inventory_db)

    assert products == []


def test_get_products(inventory_db, product):
    products = service.get_products(inventory_db)

    assert len(products) == 1
    assert products[0].id == product.id


# GET RESERVATIONS

def test_get_reservations_empty(inventory_db):
    reservations = service.get_reservations(inventory_db)

    assert reservations == []


# RESERVE PRODUCT

def test_reserve_product(inventory_db, product):
    request = schemas.ReserveRequest(
        saga_id=1,
        product_id=product.id,
        quantity=3
    )

    result = service.reserve_product(inventory_db, request)

    inventory_db.refresh(product)

    assert result["message"] == "Product reserved"
    assert product.quantity == 7

    reservations = service.get_reservations(inventory_db)

    assert len(reservations) == 1
    assert reservations[0].status == "RESERVED"
    assert reservations[0].quantity == 3


def test_reserve_product_idempotent(inventory_db, product):
    request = schemas.ReserveRequest(
        saga_id=1,
        product_id=product.id,
        quantity=3
    )

    service.reserve_product(inventory_db, request)
    result = service.reserve_product(inventory_db, request)

    inventory_db.refresh(product)

    assert result["message"] == "Product already reserved"
    assert product.quantity == 7
    assert len(service.get_reservations(inventory_db)) == 1


def test_reserve_insufficient_stock(inventory_db, product):
    request = schemas.ReserveRequest(
        saga_id=1,
        product_id=product.id,
        quantity=20
    )

    with pytest.raises(service.InsufficientStockError):
        service.reserve_product(inventory_db, request)

    inventory_db.refresh(product)

    assert product.quantity == 10
    assert service.get_reservations(inventory_db) == []


def test_reserve_product_not_found(inventory_db):
    request = schemas.ReserveRequest(
        saga_id=1,
        product_id=999,
        quantity=2
    )

    with pytest.raises(service.ProductNotFoundError):
        service.reserve_product(inventory_db, request)


# RELEASE PRODUCT

def test_release_product(inventory_db, product):
    reserve_request = schemas.ReserveRequest(
        saga_id=1,
        product_id=product.id,
        quantity=3
    )

    service.reserve_product(inventory_db, reserve_request)

    release_request = schemas.ReleaseRequest(saga_id=1)

    result = service.release_product(
        inventory_db,
        release_request
    )

    inventory_db.refresh(product)

    assert result["message"] == "Product released"
    assert product.quantity == 10

    reservation = service.get_reservations(inventory_db)[0]
    assert reservation.status == "RELEASED"


def test_release_product_idempotent(inventory_db, product):
    service.reserve_product(
        inventory_db,
        schemas.ReserveRequest(
            saga_id=1,
            product_id=product.id,
            quantity=3
        )
    )

    request = schemas.ReleaseRequest(saga_id=1)

    service.release_product(inventory_db, request)
    result = service.release_product(inventory_db, request)

    inventory_db.refresh(product)

    assert result["message"] == "Product already released"
    assert product.quantity == 10


def test_release_reservation_not_found(inventory_db):
    request = schemas.ReleaseRequest(saga_id=999)

    with pytest.raises(service.ReservationNotFoundError):
        service.release_product(inventory_db, request)


def test_reserve_after_release(inventory_db, product):
    reserve_request = schemas.ReserveRequest(
        saga_id=1,
        product_id=product.id,
        quantity=3
    )

    service.reserve_product(inventory_db, reserve_request)

    service.release_product(
        inventory_db,
        schemas.ReleaseRequest(saga_id=1)
    )

    with pytest.raises(service.ReservationAlreadyReleasedError):
        service.reserve_product(inventory_db, reserve_request)

    inventory_db.refresh(product)
    assert product.quantity == 10


# DELETE PRODUCT

def test_delete_product(inventory_db, product):
    deleted_id = service.delete_product(
        inventory_db,
        product.id
    )

    assert deleted_id == product.id
    assert service.get_products(inventory_db) == []


def test_delete_product_not_found(inventory_db):
    with pytest.raises(service.ProductNotFoundError):
        service.delete_product(inventory_db, 999)


# DELETE RESERVATION

def test_delete_reservation(inventory_db, product):
    service.reserve_product(
        inventory_db,
        schemas.ReserveRequest(
            saga_id=1,
            product_id=product.id,
            quantity=3
        )
    )

    deleted_saga_id = service.delete_reservation(
        inventory_db,
        1
    )

    assert deleted_saga_id == 1
    assert service.get_reservations(inventory_db) == []


def test_delete_reservation_not_found(inventory_db):
    with pytest.raises(service.ReservationNotFoundError):
        service.delete_reservation(inventory_db, 999)
