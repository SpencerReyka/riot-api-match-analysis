from dataclasses import dataclass
from datetime import UTC, datetime

from django.conf import settings
from django.db import transaction
from django.db.models import Avg, Count, Q
from django.utils import timezone

from .models import Match, Participant, RiotAccount
from .riot import RiotAPIError, RiotClient
from .secrets import SecretStorageError, get_riot_api_key


@dataclass(frozen=True)
class SyncResult:
    account: RiotAccount
    fetched_matches: int
    cached_matches: int


@dataclass(frozen=True)
class AccountAnalysis:
    account: RiotAccount
    games: int
    threats: int
    threat_ratio: float
    wins: int
    win_ratio: float
    average_dpm: float

    @property
    def threat_percent(self) -> float:
        return self.threat_ratio * 100

    @property
    def win_percent(self) -> float:
        return self.win_ratio * 100


def build_riot_client(*, routing_region: str, platform_region: str) -> RiotClient:
    try:
        api_key = get_riot_api_key()
    except SecretStorageError as exc:
        raise RiotAPIError("The Riot API credential is unavailable.") from exc
    return RiotClient(
        api_key,
        routing_region=routing_region,
        platform_region=platform_region,
    )


def sync_account(
    game_name: str,
    tag_line: str,
    *,
    routing_region: str | None = None,
    platform_region: str | None = None,
    client: RiotClient | None = None,
    match_count: int | None = None,
) -> SyncResult:
    routing = routing_region or settings.RIOT_DEFAULT_ROUTING
    platform = platform_region or settings.RIOT_DEFAULT_PLATFORM
    riot = client or build_riot_client(
        routing_region=routing, platform_region=platform
    )
    remote = riot.account_by_riot_id(game_name.strip(), tag_line.strip())

    account, _ = RiotAccount.objects.update_or_create(
        puuid=remote.puuid,
        defaults={
            "game_name": remote.game_name,
            "tag_line": remote.tag_line,
            "routing_region": routing,
            "platform_region": platform,
        },
    )

    match_ids = riot.aram_match_ids(
        remote.puuid, count=match_count or settings.RIOT_MATCH_COUNT
    )
    existing = set(
        Match.objects.filter(match_id__in=match_ids).values_list("match_id", flat=True)
    )
    fetched = 0

    for match_id in match_ids:
        if match_id in existing:
            Participant.objects.filter(
                match_id=match_id, puuid=account.puuid
            ).update(account=account)
            continue
        _store_match(riot.match(match_id), account)
        fetched += 1

    account.last_synced_at = timezone.now()
    account.save(update_fields=("last_synced_at", "updated_at"))
    return SyncResult(
        account=account,
        fetched_matches=fetched,
        cached_matches=len(match_ids) - fetched,
    )


@transaction.atomic
def _store_match(payload: dict, tracked_account: RiotAccount) -> Match:
    metadata = payload.get("metadata", {})
    info = payload.get("info", {})
    match_id = metadata.get("matchId")
    participants = info.get("participants")
    started_ms = int(info.get("gameStartTimestamp") or 0)
    if not match_id or not isinstance(participants, list) or not started_ms:
        raise ValueError("Riot match response is missing required fields.")

    duration = max(int(info.get("gameDuration") or 0), 1)
    match = Match.objects.create(
        match_id=match_id,
        queue_id=int(info.get("queueId") or 0),
        game_mode=str(info.get("gameMode") or ""),
        game_start=datetime.fromtimestamp(started_ms / 1000, tz=UTC),
        duration_seconds=duration,
        payload=payload,
    )

    rows = []
    for participant in participants:
        puuid = str(participant.get("puuid") or "")
        if not puuid:
            continue
        challenges = participant.get("challenges") or {}
        damage = max(int(participant.get("totalDamageDealtToChampions") or 0), 0)
        dpm = challenges.get("damagePerMinute")
        if dpm is None:
            dpm = damage / duration * 60
        rows.append(
            Participant(
                match=match,
                account=tracked_account if puuid == tracked_account.puuid else None,
                puuid=puuid,
                game_name=str(participant.get("riotIdGameName") or ""),
                tag_line=str(participant.get("riotIdTagline") or ""),
                summoner_name=str(participant.get("summonerName") or ""),
                win=bool(participant.get("win")),
                damage_per_minute=max(float(dpm), 0),
                total_damage_to_champions=damage,
            )
        )
    Participant.objects.bulk_create(rows)
    return match


def analyze_account(account: RiotAccount) -> AccountAnalysis:
    summary = account.participations.aggregate(
        games=Count("id"),
        threats=Count(
            "id", filter=Q(damage_per_minute__gt=settings.DPS_THREAT_THRESHOLD)
        ),
        wins=Count("id", filter=Q(win=True)),
        average_dpm=Avg("damage_per_minute"),
    )
    games = summary["games"] or 0
    threats = summary["threats"] or 0
    wins = summary["wins"] or 0
    return AccountAnalysis(
        account=account,
        games=games,
        threats=threats,
        threat_ratio=threats / games if games else 0,
        wins=wins,
        win_ratio=wins / games if games else 0,
        average_dpm=float(summary["average_dpm"] or 0),
    )
