from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .generated.backbone.v1.envelope_pb2 import EventEnvelope
from .generated.backbone.v1.events.riot_pb2 import RiotAnalysisRequested
from .models import AnalysisQueueGuard, AnalysisRequest, OutboxEvent
from .rate_limits import consume_public_request_quota

EVENT_TYPE = "riot.analysis.requested"
EVENT_VERSION = 1
EMITTING_SERVICE = "riot-match-analysis-web"


class AnalysisQueueFull(RuntimeError):
    pass


@dataclass(frozen=True)
class SubmissionResult:
    request: AnalysisRequest
    created: bool


def _normal(value: str) -> str:
    return value.strip().casefold()


def _envelope_for(request_row: AnalysisRequest, event_id: uuid.UUID) -> bytes:
    requested_at = request_row.requested_at.isoformat()
    payload = RiotAnalysisRequested(
        request_id=str(request_row.id),
        game_name=request_row.game_name,
        tag_line=request_row.tag_line,
        routing_region=request_row.routing_region,
        platform_region=request_row.platform_region,
        requested_at=requested_at,
    ).SerializeToString()
    return EventEnvelope(
        event_id=str(event_id),
        event_type=EVENT_TYPE,
        event_version=EVENT_VERSION,
        occurred_at=requested_at,
        service=EMITTING_SERVICE,
        correlation_id=str(request_row.id),
        payload=payload,
    ).SerializeToString()


def submit_analysis_request(
    *, game_name: str, tag_line: str, requester_hash: str
) -> SubmissionResult:
    consume_public_request_quota(requester_hash)
    now = timezone.now()
    normalized_game_name = _normal(game_name)
    normalized_tag_line = _normal(tag_line.lstrip("#"))
    cutoff = now - timedelta(seconds=settings.PUBLIC_REQUEST_COOLDOWN_SECONDS)

    with transaction.atomic():
        AnalysisQueueGuard.objects.get_or_create(pk=1)
        AnalysisQueueGuard.objects.select_for_update().get(pk=1)

        existing = (
            AnalysisRequest.objects.filter(
                normalized_game_name=normalized_game_name,
                normalized_tag_line=normalized_tag_line,
                routing_region=settings.RIOT_DEFAULT_ROUTING,
                requested_at__gte=cutoff,
            )
            .exclude(status=AnalysisRequest.Status.FAILED)
            .order_by("-requested_at")
            .first()
        )
        if existing:
            return SubmissionResult(existing, created=False)

        in_flight = AnalysisRequest.objects.filter(
            status__in=(
                AnalysisRequest.Status.QUEUED,
                AnalysisRequest.Status.PROCESSING,
            )
        ).count()
        if in_flight >= settings.PUBLIC_REQUEST_QUEUE_LIMIT:
            raise AnalysisQueueFull(
                "The analysis queue is full. Please try again a little later."
            )

        request_row = AnalysisRequest.objects.create(
            game_name=game_name.strip(),
            tag_line=tag_line.strip().lstrip("#"),
            normalized_game_name=normalized_game_name,
            normalized_tag_line=normalized_tag_line,
            routing_region=settings.RIOT_DEFAULT_ROUTING,
            platform_region=settings.RIOT_DEFAULT_PLATFORM,
            requester_hash=requester_hash,
        )
        event_id = uuid.uuid4()
        OutboxEvent.objects.create(
            id=event_id,
            event_type=EVENT_TYPE,
            event_version=EVENT_VERSION,
            payload=_envelope_for(request_row, event_id),
        )
    return SubmissionResult(request_row, created=True)
