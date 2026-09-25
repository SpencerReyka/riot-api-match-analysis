from __future__ import annotations

import hashlib
import hmac
import ipaddress
import time
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import PublicRateLimitBucket, RiotRateLimitBucket
from .riot import RiotAPIError


class PublicRateLimitExceeded(RuntimeError):
    pass


def requester_hash(request) -> str:
    raw = request.META.get("REMOTE_ADDR", "")
    if settings.TRUST_CLOUDFLARE_IP_HEADER:
        raw = request.META.get("HTTP_CF_CONNECTING_IP", raw)
    try:
        address = str(ipaddress.ip_address(raw.strip()))
    except ValueError:
        address = "unknown"
    return hmac.new(
        settings.SECRET_KEY.encode(), address.encode(), hashlib.sha256
    ).hexdigest()


def consume_public_request_quota(actor_hash: str) -> None:
    now = timezone.now()
    limits = tuple(settings.PUBLIC_REQUEST_LIMITS)
    for window_seconds, _limit in limits:
        PublicRateLimitBucket.objects.get_or_create(
            actor_hash=actor_hash,
            window_seconds=window_seconds,
            defaults={"window_started_at": now},
        )

    with transaction.atomic():
        buckets = {
            bucket.window_seconds: bucket
            for bucket in PublicRateLimitBucket.objects.select_for_update()
            .filter(
                actor_hash=actor_hash,
                window_seconds__in=[window for window, _limit in limits],
            )
            .order_by("window_seconds")
        }
        for window_seconds, limit in limits:
            bucket = buckets[window_seconds]
            if now - bucket.window_started_at >= timedelta(seconds=window_seconds):
                bucket.window_started_at = now
                bucket.request_count = 0
            if bucket.request_count >= limit:
                raise PublicRateLimitExceeded(
                    "Too many requests. Please wait before trying again."
                )
        for window_seconds, _limit in limits:
            bucket = buckets[window_seconds]
            bucket.request_count += 1
            bucket.save(
                update_fields=("window_started_at", "request_count")
            )


class RiotDatabaseRateLimiter:
    def __init__(self, routing_region: str, *, sleep=time.sleep):
        self.routing_region = routing_region
        self.sleep = sleep

    def acquire(self) -> None:
        limits = tuple(settings.RIOT_LOCAL_RATE_LIMITS)
        while True:
            now = timezone.now()
            for window_seconds, _limit in limits:
                RiotRateLimitBucket.objects.get_or_create(
                    routing_region=self.routing_region,
                    window_seconds=window_seconds,
                    defaults={"window_started_at": now},
                )

            with transaction.atomic():
                buckets = {
                    bucket.window_seconds: bucket
                    for bucket in RiotRateLimitBucket.objects.select_for_update()
                    .filter(
                        routing_region=self.routing_region,
                        window_seconds__in=[window for window, _limit in limits],
                    )
                    .order_by("window_seconds")
                }
                waits = []
                for window_seconds, limit in limits:
                    bucket = buckets[window_seconds]
                    elapsed = (now - bucket.window_started_at).total_seconds()
                    if elapsed >= window_seconds:
                        bucket.window_started_at = now
                        bucket.request_count = 0
                        elapsed = 0
                    if bucket.request_count >= limit:
                        waits.append(max(window_seconds - elapsed, 0.01))

                if not waits:
                    for window_seconds, _limit in limits:
                        bucket = buckets[window_seconds]
                        bucket.request_count += 1
                        bucket.save(
                            update_fields=("window_started_at", "request_count")
                        )
                    return

            wait_seconds = max(waits)
            if wait_seconds > 30:
                raise RiotAPIError(
                    "Riot API capacity is temporarily full. The request will be retried.",
                    429,
                )
            self.sleep(wait_seconds)
