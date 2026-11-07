import pika

RABBITMQ_HOST = "localhost"
EXCHANGE_NAME = "saga_events"
QUEUE_NAME = "inventory_queue"


def setup_queue():
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host=RABBITMQ_HOST)
    )

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
        routing_key="OrderCreated"
    )

    connection.close()