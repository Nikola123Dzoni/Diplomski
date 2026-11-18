
import pytest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from order_service.database import Base
from order_service import models

from inventory_service.database import Base as InventoryBase
from inventory_service import models as inventory_models

from payment_service.database import Base as PaymentBase
from payment_service import models as payment_models

@pytest.fixture
def payment_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )

    PaymentBase.metadata.create_all(bind=engine)

    TestingSessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False
    )

    db = TestingSessionLocal()

    try:
        yield db
    finally:
        db.close()
        PaymentBase.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture
def order_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )

    Base.metadata.create_all(bind=engine)

    TestingSessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False
    )

    db = TestingSessionLocal()

    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()

@pytest.fixture
def inventory_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )

    InventoryBase.metadata.create_all(bind=engine)

    TestingSessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False
    )

    db = TestingSessionLocal()

    try:
        yield db
    finally:
        db.close()
        InventoryBase.metadata.drop_all(bind=engine)
        engine.dispose()