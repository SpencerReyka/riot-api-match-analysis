from django.test import TestCase, override_settings

from stats.models import Match, Participant, RiotAccount
from stats.services import analyze_account, sync_account
from stats.tests.fixtures import FakeRiotClient, match_payload


@override_settings(RIOT_MATCH_COUNT=20, DPS_THREAT_THRESHOLD=1800)
class SyncAccountTests(TestCase):
    def test_fetches_and_persists_new_matches(self):
        client = FakeRiotClient(
            match_ids=["NA1_1", "NA1_2"],
            payloads={
                "NA1_1": match_payload("NA1_1", dpm=1901, win=True),
                "NA1_2": match_payload("NA1_2", dpm=1200, win=False),
            },
        )

        result = sync_account("Damage Dealer", "NA1", client=client)

        self.assertEqual(result.fetched_matches, 2)
        self.assertEqual(result.cached_matches, 0)
        self.assertEqual(Match.objects.count(), 2)
        self.assertEqual(Participant.objects.count(), 4)
        self.assertEqual(result.account.participations.count(), 2)
        self.assertIsNotNone(result.account.last_synced_at)
        self.assertEqual(client.requested_count, 20)

        analysis = analyze_account(result.account)
        self.assertEqual(analysis.games, 2)
        self.assertEqual(analysis.threats, 1)
        self.assertEqual(analysis.threat_ratio, 0.5)
        self.assertEqual(analysis.wins, 1)
        self.assertEqual(analysis.win_ratio, 0.5)
        self.assertEqual(analysis.average_dpm, 1550.5)

    def test_second_sync_reuses_cache_without_match_requests(self):
        first = FakeRiotClient(match_ids=["NA1_1"])
        sync_account("Damage Dealer", "NA1", client=first)
        second = FakeRiotClient(match_ids=["NA1_1"])

        result = sync_account("Damage Dealer", "NA1", client=second)

        self.assertEqual(result.fetched_matches, 0)
        self.assertEqual(result.cached_matches, 1)
        self.assertEqual(second.match_calls, [])
        self.assertEqual(Match.objects.count(), 1)

    def test_cached_shared_match_links_new_tracked_account(self):
        first = FakeRiotClient(match_ids=["NA1_1"])
        sync_account("Damage Dealer", "NA1", client=first)
        teammate = RiotAccount.objects.create(
            puuid="someone-else", game_name="Teammate", tag_line="NA1"
        )
        cached_participant = Participant.objects.get(puuid="someone-else")
        self.assertIsNone(cached_participant.account)

        class TeammateClient(FakeRiotClient):
            def account_by_riot_id(self, game_name, tag_line):
                from stats.riot import RiotAccountData

                return RiotAccountData("someone-else", game_name, tag_line)

        result = sync_account("Teammate", "NA1", client=TeammateClient(match_ids=["NA1_1"]))

        cached_participant.refresh_from_db()
        self.assertEqual(result.account, teammate)
        self.assertEqual(cached_participant.account, teammate)

    def test_calculates_dpm_when_challenges_value_is_absent(self):
        payload = match_payload()
        del payload["info"]["participants"][0]["challenges"]["damagePerMinute"]
        payload["info"]["participants"][0]["totalDamageDealtToChampions"] = 36000
        client = FakeRiotClient(payloads={"NA1_1": payload})

        result = sync_account("Damage Dealer", "NA1", client=client)

        participant = result.account.participations.get()
        self.assertEqual(participant.damage_per_minute, 1800)

    def test_empty_history_has_zero_ratios(self):
        account = RiotAccount.objects.create(
            puuid="empty", game_name="Empty", tag_line="NA1"
        )

        analysis = analyze_account(account)

        self.assertEqual(analysis.games, 0)
        self.assertEqual(analysis.threat_ratio, 0)
        self.assertEqual(analysis.win_ratio, 0)
