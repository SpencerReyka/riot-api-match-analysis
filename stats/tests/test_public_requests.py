import uuid
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse

from stats.backbone_worker import (
    PermanentEventError,
    decode_requested_event,
    process_requested_event,
)
from stats.generated.backbone.v1.envelope_pb2 import EventEnvelope
from stats.models import AnalysisRequest, OutboxEvent, ProcessedEvent, RiotAccount
from stats.public_requests import submit_analysis_request
from stats.riot import RiotAPIError
from stats.services import SyncResult


PUBLIC_SETTINGS = {
    "RIOT_PUBLIC_REQUESTS_ENABLED": True,
    "PUBLIC_REQUEST_LIMITS": ((600, 3), (86_400, 10)),
    "PUBLIC_REQUEST_COOLDOWN_SECONDS": 900,
    "PUBLIC_REQUEST_QUEUE_LIMIT": 100,
    "TRUST_CLOUDFLARE_IP_HEADER": True,
}


@override_settings(**PUBLIC_SETTINGS)
class PublicRequestViewTests(TestCase):
    def post(self, game_name="Damage Dealer", tag_line="NA1", **extra):
        return self.client.post(
            reverse("request-analysis"),
            {"game_name": game_name, "tag_line": tag_line, **extra},
            HTTP_CF_CONNECTING_IP="203.0.113.7",
        )

    def test_submission_persists_request_and_protobuf_outbox_atomically(self):
        response = self.post()

        request_row = AnalysisRequest.objects.get()
        event = OutboxEvent.objects.get()
        self.assertRedirects(
            response,
            reverse("analysis-request-status", args=[request_row.id]),
        )
        event_id, payload = decode_requested_event(bytes(event.payload))
        self.assertEqual(event_id, event.id)
        self.assertEqual(payload.request_id, str(request_row.id))
        self.assertEqual(payload.game_name, "Damage Dealer")

    def test_recent_duplicate_reuses_request_without_another_event(self):
        first = self.post(game_name=" Player ", tag_line="#NA1")
        second = self.post(game_name="player", tag_line="na1")

        self.assertEqual(first.url, second.url)
        self.assertEqual(AnalysisRequest.objects.count(), 1)
        self.assertEqual(OutboxEvent.objects.count(), 1)

    def test_per_ip_rate_limit_returns_429(self):
        for number in range(3):
            self.post(game_name=f"Player {number}")

        response = self.post(game_name="One Too Many")

        self.assertEqual(response.status_code, 429)
        self.assertEqual(response["Retry-After"], "600")
        self.assertContains(response, "Too many requests", status_code=429)

    def test_honeypot_is_rejected_without_creating_a_request(self):
        response = self.post(website="https://spam.example")

        self.assertEqual(response.status_code, 400)
        self.assertFalse(AnalysisRequest.objects.exists())

    @override_settings(PUBLIC_REQUEST_QUEUE_LIMIT=1)
    def test_global_queue_ceiling_returns_503(self):
        self.post(game_name="First")

        response = self.post(game_name="Second")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response["Retry-After"], "60")
        self.assertEqual(AnalysisRequest.objects.count(), 1)

    def test_status_uses_unguessable_uuid_and_is_not_cached(self):
        self.post()
        request_row = AnalysisRequest.objects.get()

        response = self.client.get(
            reverse("analysis-request-status", args=[request_row.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("no-store", response["Cache-Control"])
        self.assertEqual(response["Refresh"], "5")
        self.assertEqual(
            self.client.get(
                reverse("analysis-request-status", args=[uuid.uuid4()])
            ).status_code,
            404,
        )


class PublicRequestDisabledTests(TestCase):
    def test_disabled_submission_fails_closed(self):
        response = self.client.post(
            reverse("request-analysis"),
            {"game_name": "Player", "tag_line": "NA1"},
        )

        self.assertEqual(response.status_code, 503)
        self.assertFalse(AnalysisRequest.objects.exists())


@override_settings(**PUBLIC_SETTINGS)
class AnalysisWorkerTests(TestCase):
    def setUp(self):
        result = submit_analysis_request(
            game_name="Damage Dealer", tag_line="NA1", requester_hash="a" * 64
        )
        self.request_row = result.request
        self.outbox = OutboxEvent.objects.get()
        self.event_id, self.payload = decode_requested_event(bytes(self.outbox.payload))

    @patch("stats.backbone_worker.sync_account")
    def test_worker_completes_request_idempotently(self, sync):
        account = RiotAccount.objects.create(
            puuid="p1", game_name="Damage Dealer", tag_line="NA1"
        )
        sync.return_value = SyncResult(account, fetched_matches=2, cached_matches=1)

        process_requested_event(self.event_id, self.payload)
        process_requested_event(self.event_id, self.payload)

        self.request_row.refresh_from_db()
        self.assertEqual(self.request_row.status, AnalysisRequest.Status.COMPLETE)
        self.assertEqual(self.request_row.account, account)
        self.assertEqual(sync.call_count, 1)
        self.assertEqual(ProcessedEvent.objects.count(), 1)

    @patch(
        "stats.backbone_worker.sync_account",
        side_effect=RiotAPIError("rate limited", 429),
    )
    def test_transient_riot_failure_returns_request_to_queue(self, _sync):
        with self.assertRaisesRegex(RuntimeError, "temporarily unavailable"):
            process_requested_event(self.event_id, self.payload)

        self.request_row.refresh_from_db()
        self.assertEqual(self.request_row.status, AnalysisRequest.Status.QUEUED)
        self.assertIn("retried", self.request_row.public_message)

    @patch(
        "stats.backbone_worker.sync_account",
        side_effect=RiotAPIError("not found", 404),
    )
    def test_not_found_is_a_completed_failure_not_a_retry(self, _sync):
        process_requested_event(self.event_id, self.payload)

        self.request_row.refresh_from_db()
        self.assertEqual(self.request_row.status, AnalysisRequest.Status.FAILED)
        self.assertEqual(ProcessedEvent.objects.count(), 1)

    def test_malformed_event_is_permanent(self):
        envelope = EventEnvelope(
            event_id=str(uuid.uuid4()),
            event_type="some.other.event",
            event_version=1,
            payload=b"bad",
        )
        with self.assertRaises(PermanentEventError):
            decode_requested_event(envelope.SerializeToString())
