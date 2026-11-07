import json
import pika

RABBITMQ_HOST = "localhost"
EXCHANGE_NAME = "saga_events"


def publish_event(event_type, data):
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host=RABBITMQ_HOST)
    )

    channel = connection.channel()

    channel.exchange_declare(
        exchange=EXCHANGE_NAME,
        exchange_type="topic",
        durable=True
    )

    message = {
        "event_type": event_type,
        **data
    }

    channel.basic_publish(
        exchange=EXCHANGE_NAME,
        routing_key=event_type,
        body=json.dumps(message),
        properties=pika.BasicProperties(
            delivery_mode=2
        )
    )

    connection.close()