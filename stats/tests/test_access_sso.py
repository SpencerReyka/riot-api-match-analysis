"""Cloudflare Access sign-in.

These pin the properties that fail silently: a forged header letting someone in, a wrong-audience
token from a *different* app on the same team being accepted, and an unconfigured deployment
quietly authenticating everybody.
"""

import json
import time

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from stats import access_sso

AUD = "09476cb4134f9782d0a85bcdd82ce942e32d94c27cf695d8e5f812c9dc621df3"
OWNER = "spencer.reyka@gmail.com"
KID = "test-key-1"

_private = rsa.generate_private_key(public_exponent=65537, key_size=2048)


def _jwks():
    return {"keys": [json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(_private.public_key())) | {"kid": KID}]}


def _token(**overrides):
    now = int(time.time())
    claims = {
        "aud": AUD, "iss": access_sso.TEAM_DOMAIN, "email": OWNER, "type": "app",
        "sub": "owner", "iat": now, "exp": now + 300,
    }
    claims.update(overrides)
    return jwt.encode(claims, _private, algorithm="RS256", headers={"kid": KID})


class VerifyAccessTokenTests(TestCase):
    def setUp(self):
        access_sso._keys._keys = _jwks()
        access_sso._keys._at = time.time()

    def test_accepts_a_properly_signed_owner_token(self):
        self.assertEqual(access_sso.verify_access_token(_token(), AUD), OWNER)

    def test_rejects_a_token_for_a_different_application(self):
        # Every app on the team is signed by the same keys. Without the audience check, the
        # health-endpoint token — or any other app's — would open this one.
        other = "9b7fb629e1d694e4349a59a01b57b972a753ef3a829366206cd4bcacc6523d34"
        self.assertIsNone(access_sso.verify_access_token(_token(aud=other), AUD))

    def test_rejects_a_token_signed_by_someone_else(self):
        forged = jwt.encode(
            {"aud": AUD, "iss": access_sso.TEAM_DOMAIN, "email": OWNER, "type": "app",
             "sub": "x", "iat": int(time.time()), "exp": int(time.time()) + 300},
            rsa.generate_private_key(public_exponent=65537, key_size=2048),
            algorithm="RS256", headers={"kid": KID},
        )
        self.assertIsNone(access_sso.verify_access_token(forged, AUD))

    def test_rejects_expired_and_malformed_tokens(self):
        now = int(time.time())
        self.assertIsNone(access_sso.verify_access_token(_token(exp=now - 10, iat=now - 600), AUD))
        self.assertIsNone(access_sso.verify_access_token("not-a-jwt", AUD))
        self.assertIsNone(access_sso.verify_access_token(None, AUD))

    def test_rejects_an_identity_token_rather_than_an_application_token(self):
        self.assertIsNone(access_sso.verify_access_token(_token(type="org"), AUD))

    def test_unconfigured_audience_fails_closed(self):
        # The failure that would be invisible: a deployment missing CF_ACCESS_AUD must refuse
        # everyone, not accept anyone.
        self.assertIsNone(access_sso.verify_access_token(_token(), None))
        self.assertIsNone(access_sso.verify_access_token(_token(), ""))

    def test_unavailable_signing_keys_fail_closed(self):
        access_sso._keys._keys = None
        access_sso._keys._at = time.time()
        self.assertIsNone(access_sso.verify_access_token(_token(), AUD))


@override_settings(CF_ACCESS_AUD=AUD, CF_ACCESS_OWNER_EMAIL=OWNER)
class MiddlewareTests(TestCase):
    def setUp(self):
        access_sso._keys._keys = _jwks()
        access_sso._keys._at = time.time()

    def test_a_signed_token_signs_you_in_with_no_password(self):
        r = self.client.get("/admin/", HTTP_CF_ACCESS_JWT_ASSERTION=_token())
        self.assertIn(r.status_code, (200, 302))
        user = get_user_model().objects.get(username=OWNER)
        self.assertTrue(user.is_staff)
        self.assertFalse(user.has_usable_password(),
                         "the account exists to be logged in by Access, not by password")

    def test_the_plain_email_header_alone_gets_you_nothing(self):
        # The whole reason this verifies a JWT. This app binds 0.0.0.0:3230, so anything on the
        # VNet can reach it directly and send whatever headers it likes.
        self.client.get("/admin/", HTTP_CF_ACCESS_AUTHENTICATED_USER_EMAIL=OWNER)
        self.assertFalse(get_user_model().objects.filter(username=OWNER).exists())

    def test_a_valid_token_for_somebody_else_creates_no_account(self):
        self.client.get("/admin/", HTTP_CF_ACCESS_JWT_ASSERTION=_token(email="someone@example.com"))
        self.assertEqual(get_user_model().objects.count(), 0)

    def test_no_token_creates_no_account(self):
        self.client.get("/admin/")
        self.assertEqual(get_user_model().objects.count(), 0)


@override_settings(CF_ACCESS_AUD=AUD, CF_ACCESS_OWNER_EMAIL=OWNER)
class BackendTests(TestCase):
    """The backend's own owner check, exercised directly.

    Going through the middleware cannot test this: the middleware compares the email to the owner
    before it ever calls authenticate(), so the backend's guard is masked and a mutation removing
    it passes the suite. Anything that calls authenticate() from somewhere else — a management
    command, a future view — would meet the unguarded version.
    """

    def setUp(self):
        self.backend = access_sso.OwnerOnlyRemoteUserBackend()

    def test_creates_the_owner_once_and_reuses_it(self):
        first = self.backend.authenticate(None, remote_user=OWNER)
        second = self.backend.authenticate(None, remote_user=OWNER)
        self.assertIsNotNone(first)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(get_user_model().objects.count(), 1)
        self.assertTrue(first.is_staff and first.is_superuser)
        self.assertFalse(first.has_usable_password())

    def test_refuses_anyone_who_is_not_the_owner(self):
        self.assertIsNone(self.backend.authenticate(None, remote_user="someone@example.com"))
        self.assertIsNone(self.backend.authenticate(None, remote_user=""))
        self.assertIsNone(self.backend.authenticate(None, remote_user=None))
        self.assertEqual(get_user_model().objects.count(), 0)

    @override_settings(CF_ACCESS_OWNER_EMAIL="")
    def test_unconfigured_owner_refuses_everyone(self):
        self.assertIsNone(self.backend.authenticate(None, remote_user=OWNER))
        self.assertEqual(get_user_model().objects.count(), 0)
