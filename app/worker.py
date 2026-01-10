import json
import os
import time
from typing import Any
import pika
from sqlalchemy.orm import Session
from .database import SessionLocal
from .models import NotificationDB, DeliveryAttemptDB

QUEUE_NAME = os.getenv("PAYMENTS_QUEUE", "payments")

def _make_notification_from_event(event: dict[str, Any]) -> tuple[NotificationDB, DeliveryAttemptDB]:
    """
    Convert a payment_created event into a NotificationDB + DeliveryAttemptDB.
    """
    payment_id = event.get("payment_id")
    user_id = event.get("user_id")

    reference = f"payment_created:{payment_id}"

    notif = NotificationDB(
        reference=reference,
        recipient=f"user{user_id}",
        channel="email",
        message=f"Payment {payment_id} created for user {user_id}.",
        status="pending",
    )

    attempt = DeliveryAttemptDB(
        provider="rabbitmq-worker",
        result="queued",
        attempt_no=1,
        notification=notif,
    )
    return notif, attempt

def handle_message(db: Session, body: bytes) -> None:
    """
    Process one RabbitMQ message and persist the notification.
    Raises on invalid content to allow a retry strategy (we ack only on success).
    """
    payload = json.loads(body.decode("utf-8"))

    if payload.get("event") != "payment_created":
        return

    notif, _attempt = _make_notification_from_event(payload)

    existing = db.query(NotificationDB).filter(NotificationDB.reference == notif.reference).first()
    if existing:
        return

    db.add(notif)
    db.commit()

def run_worker() -> None:
    rabbit_url = os.getenv("RABBIT_URL")
    if not rabbit_url:
        raise RuntimeError("RABBIT_URL is not set")

    params = pika.URLParameters(rabbit_url)

    while True:
        try:
            connection = pika.BlockingConnection(params)
            break
        except pika.exceptions.AMQPConnectionError:
            time.sleep(2)

    channel = connection.channel()
    channel.queue_declare(queue=QUEUE_NAME, durable=True)
    channel.basic_qos(prefetch_count=1)

    def _callback(ch, method, properties, body): 
        db = SessionLocal()
        try:
            handle_message(db, body)
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception:
            db.rollback()

        finally:
            db.close()

    channel.basic_consume(queue=QUEUE_NAME, on_message_callback=_callback)
    try:
        channel.start_consuming()
    finally:
        connection.close()

if __name__ == "__main__":
    run_worker()
