import uuid

from django.db import models


class ApplicationSecret(models.Model):
    """Encrypted application credentials; plaintext must never be persisted."""

    RIOT_API_KEY = "riot_api_key"

    name = models.CharField(max_length=64, primary_key=True, editable=False)
    encrypted_value = models.TextField(editable=False)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.CharField(max_length=150, blank=True, editable=False)

    def __str__(self) -> str:
        return self.name


class RiotAccount(models.Model):
    puuid = models.CharField(max_length=128, unique=True)
    game_name = models.CharField(max_length=32)
    tag_line = models.CharField(max_length=8)
    platform_region = models.CharField(max_length=8, default="na1")
    routing_region = models.CharField(max_length=16, default="americas")
    last_synced_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("game_name", "tag_line", "routing_region"),
                name="unique_riot_id_per_routing_region",
            )
        ]
        ordering = ("game_name", "tag_line")

    @property
    def riot_id(self) -> str:
        return f"{self.game_name}#{self.tag_line}"

    def __str__(self) -> str:
        return self.riot_id


class Match(models.Model):
    match_id = models.CharField(max_length=64, primary_key=True)
    queue_id = models.PositiveIntegerField(db_index=True)
    game_mode = models.CharField(max_length=32)
    game_start = models.DateTimeField(db_index=True)
    duration_seconds = models.PositiveIntegerField()
    payload = models.JSONField()
    cached_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-game_start",)

    def __str__(self) -> str:
        return self.match_id


class Participant(models.Model):
    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name="participants")
    account = models.ForeignKey(
        RiotAccount,
        on_delete=models.SET_NULL,
        related_name="participations",
        null=True,
        blank=True,
    )
    puuid = models.CharField(max_length=128)
    game_name = models.CharField(max_length=32, blank=True)
    tag_line = models.CharField(max_length=8, blank=True)
    summoner_name = models.CharField(max_length=64, blank=True)
    win = models.BooleanField()
    damage_per_minute = models.FloatField()
    total_damage_to_champions = models.PositiveIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("match", "puuid"),
                name="unique_participant_per_match",
            )
        ]
        indexes = [models.Index(fields=("puuid", "match"))]

    def __str__(self) -> str:
        return f"{self.match_id}: {self.game_name or self.summoner_name or self.puuid}"


class AnalysisRequest(models.Model):
    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        PROCESSING = "processing", "Processing"
        COMPLETE = "complete", "Complete"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    game_name = models.CharField(max_length=32)
    tag_line = models.CharField(max_length=8)
    normalized_game_name = models.CharField(max_length=32, editable=False)
    normalized_tag_line = models.CharField(max_length=8, editable=False)
    platform_region = models.CharField(max_length=8, default="na1")
    routing_region = models.CharField(max_length=16, default="americas")
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.QUEUED, db_index=True
    )
    account = models.ForeignKey(
        RiotAccount,
        on_delete=models.SET_NULL,
        related_name="analysis_requests",
        null=True,
        blank=True,
    )
    requester_hash = models.CharField(max_length=64, editable=False, db_index=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    public_message = models.CharField(max_length=240, blank=True)
    requested_at = models.DateTimeField(auto_now_add=True, db_index=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-requested_at",)
        indexes = [
            models.Index(
                fields=("normalized_game_name", "normalized_tag_line", "routing_region"),
                name="analysis_request_riot_id_idx",
            )
        ]

    @property
    def riot_id(self) -> str:
        return f"{self.game_name}#{self.tag_line}"


class OutboxEvent(models.Model):
    """A Backbone protobuf envelope persisted with its originating business write."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_type = models.CharField(max_length=120, db_index=True)
    event_version = models.PositiveSmallIntegerField(default=1)
    payload = models.BinaryField(editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    published_at = models.DateTimeField(null=True, blank=True, db_index=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    last_error = models.CharField(max_length=240, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("created_at",)


class ProcessedEvent(models.Model):
    event_id = models.UUIDField()
    processed_by = models.CharField(max_length=80)
    processed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("event_id", "processed_by"), name="unique_processed_event"
            )
        ]


class PublicRateLimitBucket(models.Model):
    actor_hash = models.CharField(max_length=64)
    window_seconds = models.PositiveIntegerField()
    window_started_at = models.DateTimeField()
    request_count = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("actor_hash", "window_seconds"),
                name="unique_public_rate_limit_bucket",
            )
        ]


class RiotRateLimitBucket(models.Model):
    """Shared process-safe headroom below Riot's per-region application limit."""

    routing_region = models.CharField(max_length=16)
    window_seconds = models.PositiveIntegerField()
    window_started_at = models.DateTimeField()
    request_count = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("routing_region", "window_seconds"),
                name="unique_riot_rate_limit_bucket",
            )
        ]


class AnalysisQueueGuard(models.Model):
    """Singleton row used to serialize queue-depth checks across web workers."""

    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
