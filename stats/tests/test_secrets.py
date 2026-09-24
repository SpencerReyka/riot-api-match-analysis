from django.test import TestCase, override_settings

from stats.models import ApplicationSecret
from stats.secrets import SecretStorageError, get_riot_api_key, set_riot_api_key

TEST_ENCRYPTION_KEY = "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA="
OTHER_ENCRYPTION_KEY = "MTExMTExMTExMTExMTExMTExMTExMTExMTExMTExMTExMTE="


@override_settings(
    RIOT_API_KEY="RGAPI-environment-fallback",
    RIOT_API_KEY_ENCRYPTION_KEY=TEST_ENCRYPTION_KEY,
)
class SecretStorageTests(TestCase):
    def test_uses_environment_fallback_without_database_override(self):
        self.assertEqual(get_riot_api_key(), "RGAPI-environment-fallback")

    def test_database_override_is_encrypted_and_takes_precedence(self):
        set_riot_api_key("RGAPI-database-value", updated_by="operator")

        stored = ApplicationSecret.objects.get(name=ApplicationSecret.RIOT_API_KEY)
        self.assertNotIn("RGAPI-database-value", stored.encrypted_value)
        self.assertEqual(get_riot_api_key(), "RGAPI-database-value")

    def test_wrong_master_key_fails_closed(self):
        set_riot_api_key("RGAPI-database-value")

        with override_settings(RIOT_API_KEY_ENCRYPTION_KEY=OTHER_ENCRYPTION_KEY):
            with self.assertRaises(SecretStorageError):
                get_riot_api_key()
