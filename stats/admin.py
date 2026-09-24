from django.contrib import admin

from .models import Match, Participant, RiotAccount


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
