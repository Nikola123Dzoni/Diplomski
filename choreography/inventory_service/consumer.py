
import json
import pika

from .rabbitmq import setup_queue, RABBITMQ_HOST, QUEUE_NAME


def process_message(ch, method, properties, body):
    event = json.loads(body)

    print("Primljen dogadjaj:", event, flush=True)

    # Za sada samo potvrdjujemo prijem poruke
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
