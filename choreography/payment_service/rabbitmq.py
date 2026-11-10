import json
import pika

RABBITMQ_HOST = "localhost"
EXCHANGE_NAME = "saga_events"
QUEUE_NAME = "payment_queue"


def setup_queue():
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host=RABBITMQ_HOST)
    )

    try:
        channel = connection.channel()

        channel.exchange_declare(
            exchange=EXCHANGE_NAME,
            exchange_type="topic",
            durable=True
        )

        channel.queue_declare(
            queue=QUEUE_NAME,
            durable=True
        )

        channel.queue_bind(
            exchange=EXCHANGE_NAME,
            queue=QUEUE_NAME,
            routing_key="InventoryReserved"
        )
    finally:
        connection.close()


def publish_event(event_type, data):
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host=RABBITMQ_HOST)
    )

    try:
        channel = connection.channel()

        channel.exchange_declare(
            exchange=EXCHANGE_NAME,
            exchange_type="topic",
            durable=True
        )

        event = {
            "event_type": event_type,
            **data
        }

        channel.confirm_delivery()

        channel.basic_publish(
            exchange=EXCHANGE_NAME,
            routing_key=event_type,
            body=json.dumps(event),
            mandatory=True,
            properties=pika.BasicProperties(
                delivery_mode=2
            )
        )
    finally:
        connection.close()