
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

    print("Payment primio dogadjaj:", event, flush=True)

    if event["event_type"] != "InventoryReserved":
        ch.basic_ack(delivery_tag=method.delivery_tag)
        return

    db = SessionLocal()

    try:
        request = schemas.PaymentCreate(
            saga_id=event["saga_id"],
            order_id=event["order_id"],
            account_id=event["account_id"],
            amount=event["amount"]
        )

        result = service.pay(db, request)

        print("Placanje uspesno:", result)


        # Objavljujemo novi dogadjaj
        publish_event(
            "PaymentCompleted",
            {
                "saga_id": event["saga_id"],
                "order_id": event["order_id"],
                "product_id": event["product_id"],
                "account_id": event["account_id"],
                "quantity": event["quantity"],
                "amount": event["amount"]
            }
        )
        print("PaymentCompleted objavljen!", flush=True)


    except Exception as e:
        db.rollback()
        print("Greska pri placanju:", e)

        # Za sada ne potvrdjujemo neuspesnu obradu.
        # Kasnije razlikujemo poslovni neuspeh
        # od privremene tehnicke greske.
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

    print("Payment Consumer ceka poruke...", flush=True)

    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        print("Payment Consumer zaustavljen.")
        channel.stop_consuming()
    finally:
        if connection.is_open:
            connection.close()


if __name__ == "__main__":
    start_consumer()
