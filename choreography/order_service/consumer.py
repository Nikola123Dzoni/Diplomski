import json
import pika

from .rabbitmq import (
    setup_queue,
    RABBITMQ_HOST,
    QUEUE_NAME
)

from .database import SessionLocal
from . import service

def process_message(ch, method, properties, body):
    event = json.loads(body)

    print("Order primio dogadjaj:", event, flush=True)

    if event["event_type"] == "PaymentCompleted":
        db = SessionLocal()

        try:
            order = service.update_order_status(
                db,
                event["order_id"],
                "PAID"
            )

            print("Order status promenjen u PAID:", order.id)

        except Exception as e:
            db.rollback()
            print("Greska pri azuriranju ordera:", e)
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

    print("Order Consumer ceka poruke...", flush=True)

    channel.start_consuming()


if __name__ == "__main__":
    start_consumer()