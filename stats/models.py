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
