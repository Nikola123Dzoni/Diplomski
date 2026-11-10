
import json
import pika

from .rabbitmq import setup_queue, RABBITMQ_HOST, QUEUE_NAME
from .database import SessionLocal
from . import service, schemas


def process_message(ch, method, properties, body):
    event = json.loads(body)

    if event["event_type"] != "OrderCreated":
        ch.basic_ack(delivery_tag=method.delivery_tag)
        return

    db = SessionLocal()

    try:
        request = schemas.ReserveRequest(
            saga_id=event["saga_id"],
            product_id=event["product_id"],
            quantity=event["quantity"]
        )

        result = service.reserve_product(db, request)

        print("Rezervacija uspesna:", result)

        # Sledeci korak:
        # Objaviti InventoryReserved

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()

    # Privremeno: kasnije ACK tek nakon
    # pouzdanog objavljivanja InventoryReserved
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
