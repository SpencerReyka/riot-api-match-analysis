from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from stats.models import ApplicationSecret, RiotAccount
from stats.riot import RiotAPIError
from stats.secrets import get_riot_api_key
from stats.services import SyncResult

TEST_ENCRYPTION_KEY = "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA="


class ViewTests(TestCase):
    def setUp(self):
        self.staff = get_user_model().objects.create_user(
            username="operator", is_staff=True
        )

    def test_dashboard_renders_read_only_state_without_staff_session(self):
        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Read-only archive")
        self.assertContains(response, "No suspects yet")
        self.assertIn("script-src 'none'", response["Content-Security-Policy"])
        self.assertEqual(response["X-Frame-Options"], "DENY")
        self.assertEqual(response["Referrer-Policy"], "no-referrer")

    def test_staff_dashboard_renders_configuration_state(self):
        self.client.force_login(self.staff)

        response = self.client.get(reverse("dashboard"))

        self.assertContains(response, "Riot API key required")

    @override_settings(RIOT_API_KEY="configured")
    @patch("stats.views.sync_account")
    def test_add_account_syncs_and_redirects_to_detail(self, sync):
        self.client.force_login(self.staff)
        account = RiotAccount.objects.create(
            puuid="p1", game_name="Player", tag_line="NA1"
        )
        sync.return_value = SyncResult(account, fetched_matches=3, cached_matches=2)

        response = self.client.post(
            reverse("add-account"), {"game_name": " Player ", "tag_line": "#NA1"}
        )

        self.assertRedirects(response, reverse("account-detail", args=[account.pk]))
        sync.assert_called_once_with(game_name="Player", tag_line="NA1")

    @override_settings(RIOT_API_KEY="configured")
    @patch("stats.views.sync_account", side_effect=RiotAPIError("expired key", 403))
    def test_add_account_reports_api_error_without_server_error(self, _sync):
        self.client.force_login(self.staff)
        response = self.client.post(
            reverse("add-account"),
            {"game_name": "Player", "tag_line": "NA1"},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "expired key")

    def test_add_account_rejects_get(self):
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(reverse("add-account")).status_code, 405)

    def test_anonymous_user_cannot_import_or_refresh(self):
        account = RiotAccount.objects.create(
            puuid="p1", game_name="Player", tag_line="NA1"
        )

        add = self.client.post(
            reverse("add-account"), {"game_name": "Player", "tag_line": "NA1"}
        )
        refresh = self.client.post(reverse("refresh-account", args=[account.pk]))

        self.assertRedirects(
            add, f"{reverse('admin:login')}?next={reverse('add-account')}"
        )
        self.assertRedirects(
            refresh,
            f"{reverse('admin:login')}?next={reverse('refresh-account', args=[account.pk])}",
        )

    def test_health_reports_database_only(self):
        response = self.client.get(reverse("health"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"ok": True, "database": True})

    def test_api_settings_requires_staff_login(self):
        response = self.client.get(reverse("api-settings"))

        self.assertRedirects(
            response, f"{reverse('admin:login')}?next={reverse('api-settings')}"
        )

    def test_admin_policy_allows_only_same_origin_scripts(self):
        response = self.client.get(reverse("admin:login"))

        policy = response["Content-Security-Policy"]
        self.assertIn("script-src 'self'", policy)
        self.assertNotIn("unsafe-inline", policy)

    @override_settings(RIOT_API_KEY_ENCRYPTION_KEY=TEST_ENCRYPTION_KEY)
    @patch("stats.views.RiotClient.platform_status", return_value={"id": "NA1"})
    def test_staff_can_validate_and_store_encrypted_api_key(self, _status):
        self.client.force_login(self.staff)

        response = self.client.post(
            reverse("api-settings"), {"api_key": "RGAPI-replacement"}
        )

        self.assertRedirects(response, reverse("api-settings"))
        settings_response = self.client.get(reverse("api-settings"))
        self.assertIn("no-store", settings_response["Cache-Control"])
        stored = ApplicationSecret.objects.get(name=ApplicationSecret.RIOT_API_KEY)
        self.assertNotIn("RGAPI-replacement", stored.encrypted_value)
        self.assertEqual(stored.updated_by, "operator")
        self.assertEqual(get_riot_api_key(), "RGAPI-replacement")

    @override_settings(RIOT_API_KEY_ENCRYPTION_KEY=TEST_ENCRYPTION_KEY)
    @patch(
        "stats.views.RiotClient.platform_status",
        side_effect=RiotAPIError("The Riot API key is missing, expired, or unauthorized.", 403),
    )
    def test_rejected_api_key_is_not_stored(self, _status):
        self.client.force_login(self.staff)

        response = self.client.post(
            reverse("api-settings"), {"api_key": "RGAPI-expired"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "expired")
        self.assertFalse(ApplicationSecret.objects.exists())
