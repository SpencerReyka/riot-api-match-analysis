from django.contrib import admin

from .models import AnalysisRequest, Match, OutboxEvent, Participant, RiotAccount


@admin.register(RiotAccount)
class RiotAccountAdmin(admin.ModelAdmin):
    list_display = ("riot_id", "platform_region", "last_synced_at")
    search_fields = ("game_name", "tag_line", "puuid")


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ("match_id", "queue_id", "game_mode", "game_start")
    search_fields = ("match_id",)
    list_filter = ("queue_id", "game_mode")


@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = ("match", "game_name", "win", "damage_per_minute")
    search_fields = ("game_name", "tag_line", "summoner_name", "puuid")
    list_filter = ("win",)


@admin.register(AnalysisRequest)
class AnalysisRequestAdmin(admin.ModelAdmin):
    list_display = ("riot_id", "status", "attempts", "requested_at", "finished_at")
    search_fields = ("game_name", "tag_line", "id")
    list_filter = ("status", "routing_region")
    readonly_fields = (
        "id",
        "normalized_game_name",
        "normalized_tag_line",
        "requester_hash",
        "requested_at",
        "started_at",
        "finished_at",
    )


@admin.register(OutboxEvent)
class OutboxEventAdmin(admin.ModelAdmin):
    list_display = ("id", "event_type", "attempts", "created_at", "published_at")
    list_filter = ("event_type", "published_at", "failed_at")
    readonly_fields = (
        "id",
        "event_type",
        "event_version",
        "payload",
        "created_at",
        "published_at",
        "attempts",
        "last_error",
        "failed_at",
    )

    def has_add_permission(self, request):
        return False
