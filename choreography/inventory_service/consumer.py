
import json
import pika

from .rabbitmq import (
    setup_queue,
    RABBITMQ_HOST,
    QUEUE_NAME,
    publish_event
)
from .database import SessionLocal
from . import service, schemas


def process_message(ch, method, properties, body):
    event = json.loads(body)

    print("Inventory primio dogadjaj:", event, flush=True)

    if event["event_type"] not in (
        "OrderCreated",
        "PaymentFailed"
    ):
        ch.basic_ack(delivery_tag=method.delivery_tag)
        return

    db = SessionLocal()

    try:
        if event["event_type"] == "OrderCreated":

            request = schemas.ReserveRequest(
                saga_id=event["saga_id"],
                product_id=event["product_id"],
                quantity=event["quantity"]
            )

            result = service.reserve_product(db, request)

            print("Rezervacija uspesna:", result)

            publish_event(
                "InventoryReserved",
                {
                    "saga_id": event["saga_id"],
                    "order_id": event["order_id"],
                    "product_id": event["product_id"],
                    "account_id": event["account_id"],
                    "quantity": event["quantity"],
                    "amount": event["amount"]
                }
            )

            print("InventoryReserved poslat!", flush=True)

        elif event["event_type"] == "PaymentFailed":

            request = schemas.ReleaseRequest(
                saga_id=event["saga_id"]
            )

            result = service.release_product(db, request)

            print("Rezervacija oslobodjena:", result, flush=True)

            publish_event(
                "InventoryReleased",
                {
                    "saga_id": event["saga_id"],
                    "order_id": event["order_id"],
                    "product_id": event["product_id"]
                }
            )

            print("InventoryReleased poslat!", flush=True)

    except service.InsufficientStockError:
        db.rollback()

        print("Nema dovoljno proizvoda!", flush=True)

        publish_event(
            "InventoryReservationFailed",
            {
                "saga_id": event["saga_id"],
                "order_id": event["order_id"],
                "product_id": event["product_id"]
            }
        )

        print("InventoryReservationFailed poslat!", flush=True)

    except Exception as e:
        db.rollback()
        print("Greska u Inventory Consumer-u:", e, flush=True)
        raise

    finally:
        db.close()

    ch.basic_ack(delivery_tag=method.delivery_tag)


def start_consumer():
    setup_queue()

    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host=RABBITMQ_HOST)
    )

    channel = connection.channel()

    channel.basic_qos(prefetch_count=1)

    channel.basic_consume(
        queue=QUEUE_NAME,
        on_message_callback=process_message,
        auto_ack=False
    )

    print("Inventory Consumer ceka poruke...", flush=True)

    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        print("Inventory Consumer zaustavljen.")
        channel.stop_consuming()
    finally:
        if connection.is_open:
            connection.close()


if __name__ == "__main__":
    start_consumer()
