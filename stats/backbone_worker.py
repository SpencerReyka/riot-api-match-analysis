from __future__ import annotations

import logging
import os
import signal
import uuid
from datetime import timedelta
from pathlib import Path

import pika
from django.conf import settings
from django.db import close_old_connections, transaction
from django.utils import timezone
from google.protobuf.message import DecodeError

from .generated.backbone.v1.envelope_pb2 import EventEnvelope
from .generated.backbone.v1.events.riot_pb2 import RiotAnalysisRequested
from .models import AnalysisRequest, OutboxEvent, ProcessedEvent
from .public_requests import EVENT_TYPE, EVENT_VERSION
from .riot import RiotAPIError
from .services import sync_account

logger = logging.getLogger(__name__)

EXCHANGE = "backbone"
WORKER_SERVICE = "riot-analysis-worker"
QUEUE = f"backbone.{WORKER_SERVICE}"
RETRY_DELAY_MS = 10_000
RETRY_QUEUE = f"{QUEUE}.retry.{RETRY_DELAY_MS}"
DLQ = f"{QUEUE}.dlq"
ATTEMPTS_HEADER = "x-backbone-attempts"
MAX_ATTEMPTS = 5
HEARTBEAT_FILE = Path(
    os.getenv("WORKER_HEARTBEAT_PATH", "/home/app/riot-analysis-worker-heartbeat")
)


class PermanentEventError(RuntimeError):
    pass


class TransientEventError(RuntimeError):
    pass


def decode_requested_event(body: bytes) -> tuple[uuid.UUID, RiotAnalysisRequested]:
    try:
        envelope = EventEnvelope.FromString(body)
        event_id = uuid.UUID(envelope.event_id)
        payload = RiotAnalysisRequested.FromString(envelope.payload)
        request_id = uuid.UUID(payload.request_id)
    except (DecodeError, ValueError) as exc:
        raise PermanentEventError("Malformed Backbone event") from exc
    if envelope.event_type != EVENT_TYPE or envelope.event_version != EVENT_VERSION:
        raise PermanentEventError("Unexpected Backbone event type or version")
    if not all(
        (
            payload.game_name,
            payload.tag_line,
            payload.routing_region,
            payload.platform_region,
        )
    ):
        raise PermanentEventError("Analysis event is missing required fields")
    if request_id.int == 0:
        raise PermanentEventError("Analysis event has an invalid request id")
    return event_id, payload


def _mark_failed(
    request_id: uuid.UUID, message: str, *, event_id: uuid.UUID | None = None
) -> None:
    with transaction.atomic():
        AnalysisRequest.objects.filter(pk=request_id).update(
            status=AnalysisRequest.Status.FAILED,
            public_message=message,
            finished_at=timezone.now(),
        )
        if event_id:
            ProcessedEvent.objects.get_or_create(
                event_id=event_id, processed_by=WORKER_SERVICE
            )


def process_requested_event(event_id: uuid.UUID, payload: RiotAnalysisRequested) -> None:
    request_id = uuid.UUID(payload.request_id)
    close_old_connections()
    with transaction.atomic():
        if ProcessedEvent.objects.filter(
            event_id=event_id, processed_by=WORKER_SERVICE
        ).exists():
            return
        try:
            request_row = AnalysisRequest.objects.select_for_update().get(pk=request_id)
        except AnalysisRequest.DoesNotExist as exc:
            raise PermanentEventError("Analysis request does not exist") from exc

        if request_row.status in (
            AnalysisRequest.Status.COMPLETE,
            AnalysisRequest.Status.FAILED,
        ):
            ProcessedEvent.objects.get_or_create(
                event_id=event_id, processed_by=WORKER_SERVICE
            )
            return
        stale_before = timezone.now() - timedelta(minutes=15)
        if (
            request_row.status == AnalysisRequest.Status.PROCESSING
            and request_row.started_at
            and request_row.started_at > stale_before
        ):
            raise TransientEventError("Analysis request is already being processed")
        request_row.status = AnalysisRequest.Status.PROCESSING
        request_row.started_at = timezone.now()
        request_row.attempts += 1
        request_row.public_message = ""
        request_row.save(
            update_fields=("status", "started_at", "attempts", "public_message")
        )

    try:
        result = sync_account(
            payload.game_name,
            payload.tag_line,
            routing_region=payload.routing_region,
            platform_region=payload.platform_region,
        )
    except RiotAPIError as exc:
        if exc.status_code == 404:
            _mark_failed(
                request_id, "That Riot ID could not be found.", event_id=event_id
            )
            return
        if exc.status_code == 429 or (exc.status_code and exc.status_code >= 500):
            AnalysisRequest.objects.filter(pk=request_id).update(
                status=AnalysisRequest.Status.QUEUED,
                public_message="Riot is busy; this request will be retried.",
                started_at=None,
            )
            raise TransientEventError("Riot API temporarily unavailable") from exc
        _mark_failed(
            request_id, "Analysis is temporarily unavailable.", event_id=event_id
        )
        return
    except ValueError:
        _mark_failed(
            request_id,
            "Riot returned match data that could not be analyzed.",
            event_id=event_id,
        )
        return
    except Exception:
        AnalysisRequest.objects.filter(pk=request_id).update(
            status=AnalysisRequest.Status.QUEUED,
            public_message="The worker hit a temporary error; this request will be retried.",
            started_at=None,
        )
        raise

    with transaction.atomic():
        request_row = AnalysisRequest.objects.select_for_update().get(pk=request_id)
        request_row.status = AnalysisRequest.Status.COMPLETE
        request_row.account = result.account
        request_row.finished_at = timezone.now()
        request_row.public_message = ""
        request_row.save(
            update_fields=("status", "account", "finished_at", "public_message")
        )
        ProcessedEvent.objects.get_or_create(
            event_id=event_id, processed_by=WORKER_SERVICE
        )


def declare_topology(channel) -> None:
    channel.exchange_declare(exchange=EXCHANGE, exchange_type="topic", durable=True)
    channel.queue_declare(queue=DLQ, durable=True)
    channel.queue_declare(
        queue=RETRY_QUEUE,
        durable=True,
        arguments={
            "x-message-ttl": RETRY_DELAY_MS,
            "x-dead-letter-exchange": "",
            "x-dead-letter-routing-key": QUEUE,
        },
    )
    channel.queue_declare(
        queue=QUEUE,
        durable=True,
        arguments={
            "x-dead-letter-exchange": "",
            "x-dead-letter-routing-key": DLQ,
        },
    )
    channel.queue_bind(queue=QUEUE, exchange=EXCHANGE, routing_key=EVENT_TYPE)


def publish_outbox_batch(channel, *, batch_size: int = 20) -> int:
    published = 0
    for event_id in list(
        OutboxEvent.objects.filter(published_at__isnull=True, failed_at__isnull=True)
        .order_by("created_at")
        .values_list("id", flat=True)[:batch_size]
    ):
        with transaction.atomic():
            event = OutboxEvent.objects.select_for_update().get(pk=event_id)
            if event.published_at or event.failed_at:
                continue
            try:
                confirmed = channel.basic_publish(
                    exchange=EXCHANGE,
                    routing_key=event.event_type,
                    body=bytes(event.payload),
                    properties=pika.BasicProperties(
                        content_type="application/protobuf", delivery_mode=2
                    ),
                    mandatory=True,
                )
                if confirmed is False:
                    raise RuntimeError("RabbitMQ did not confirm the publication")
            except Exception as exc:
                event.attempts += 1
                event.last_error = type(exc).__name__[:240]
                if event.attempts >= 20:
                    event.failed_at = timezone.now()
                event.save(
                    update_fields=("attempts", "last_error", "failed_at")
                )
                raise
            event.published_at = timezone.now()
            event.attempts += 1
            event.last_error = ""
            event.save(
                update_fields=("published_at", "attempts", "last_error")
            )
            published += 1
    return published


class AnalysisWorker:
    def __init__(self, rabbitmq_url: str):
        parameters = pika.URLParameters(rabbitmq_url)
        parameters.heartbeat = 600
        parameters.blocked_connection_timeout = 60
        self.connection = pika.BlockingConnection(parameters)
        self.publish_channel = self.connection.channel()
        self.publish_channel.confirm_delivery()
        self.consume_channel = self.connection.channel()
        declare_topology(self.publish_channel)
        declare_topology(self.consume_channel)
        self.consume_channel.basic_qos(prefetch_count=1)
        self.stopping = False

    def _consume(self, channel, method, properties, body) -> None:
        raw_attempts = (properties.headers or {}).get(ATTEMPTS_HEADER, 0)
        try:
            attempts = max(int(raw_attempts), 0)
        except (TypeError, ValueError):
            attempts = 0
        request_id = None
        event_id = None
        try:
            event_id, payload = decode_requested_event(body)
            request_id = uuid.UUID(payload.request_id)
            process_requested_event(event_id, payload)
        except PermanentEventError:
            logger.exception("Rejecting permanent analysis event failure")
            channel.basic_nack(method.delivery_tag, requeue=False)
            return
        except Exception:
            next_attempt = attempts + 1
            if next_attempt >= MAX_ATTEMPTS:
                logger.exception("Analysis event exhausted retries")
                if request_id:
                    _mark_failed(
                        request_id,
                        "Analysis could not be completed after several attempts.",
                        event_id=event_id,
                    )
                channel.basic_nack(method.delivery_tag, requeue=False)
                return
            try:
                channel.basic_publish(
                    exchange="",
                    routing_key=RETRY_QUEUE,
                    body=body,
                    properties=pika.BasicProperties(
                        content_type="application/protobuf",
                        delivery_mode=2,
                        headers={ATTEMPTS_HEADER: next_attempt},
                    ),
                )
                channel.basic_ack(method.delivery_tag)
            except Exception:
                logger.exception("Could not park analysis event for retry")
                channel.basic_nack(method.delivery_tag, requeue=True)
            return
        channel.basic_ack(method.delivery_tag)

    def stop(self, *_args) -> None:
        self.stopping = True

    def run(self, *, once: bool = False) -> None:
        self.consume_channel.basic_consume(queue=QUEUE, on_message_callback=self._consume)
        while not self.stopping:
            close_old_connections()
            publish_outbox_batch(self.publish_channel)
            self.connection.process_data_events(time_limit=1)
            HEARTBEAT_FILE.touch()
            if once:
                break

    def close(self) -> None:
        if self.connection.is_open:
            self.connection.close()


def run_worker(*, once: bool = False) -> None:
    if not settings.BACKBONE_RABBITMQ_URL:
        raise RuntimeError("BACKBONE_RABBITMQ_URL is not configured")
    worker = AnalysisWorker(settings.BACKBONE_RABBITMQ_URL)
    signal.signal(signal.SIGTERM, worker.stop)
    signal.signal(signal.SIGINT, worker.stop)
    try:
        worker.run(once=once)
    finally:
        worker.close()
