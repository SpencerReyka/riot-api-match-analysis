from io import StringIO
from unittest.mock import patch

from django.core.management import CommandError, call_command
from django.test import TestCase

from stats.models import RiotAccount
from stats.services import SyncResult


class SyncAccountsCommandTests(TestCase):
    @patch("stats.management.commands.sync_accounts.sync_account")
    def test_syncs_explicit_riot_id(self, sync):
        account = RiotAccount.objects.create(
            puuid="p1", game_name="Player", tag_line="NA1"
        )
        sync.return_value = SyncResult(account, fetched_matches=2, cached_matches=3)
        stdout = StringIO()

        call_command("sync_accounts", "Player#NA1", stdout=stdout)

        sync.assert_called_once_with(
            "Player",
            "NA1",
            routing_region=None,
            platform_region=None,
        )
        self.assertIn("2 new, 3 cached", stdout.getvalue())

    @patch("stats.management.commands.sync_accounts.sync_account")
    def test_all_preserves_stored_regions(self, sync):
        account = RiotAccount.objects.create(
            puuid="p1",
            game_name="Player",
            tag_line="EUW",
            routing_region="europe",
            platform_region="euw1",
        )
        sync.return_value = SyncResult(account, fetched_matches=0, cached_matches=1)

        call_command("sync_accounts", "--all", stdout=StringIO())

        sync.assert_called_once_with(
            "Player",
            "EUW",
            routing_region="europe",
            platform_region="euw1",
        )

    def test_rejects_missing_target(self):
        with self.assertRaisesMessage(CommandError, "Provide at least one"):
            call_command("sync_accounts")
