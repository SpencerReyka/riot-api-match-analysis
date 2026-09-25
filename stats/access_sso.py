"""Sign in with Cloudflare Access instead of a Django password.

Access already authenticates every request that reaches this app — Google login, owner-only
policy — so a second username and password is friction, not security. This turns that existing
identity into a Django session.

**It verifies a signed JWT, never an identity header.** Cloudflare forwards both
``Cf-Access-Authenticated-User-Email`` (plain text) and ``Cf-Access-Jwt-Assertion`` (signed).
Trusting the first would be a hole rather than a feature here: this app binds ``0.0.0.0:3230``,
so anything else inside ``10.0.0.0/24`` can reach it directly, skip Access, and simply send the
header. Only a token Cloudflare actually signed proves the request came through the front door.

Mirrors ``personal-site/lib/access.ts``, which does the same job in TypeScript and has tests:
same issuer, same audience check, same owner comparison, same fail-closed behaviour.
"""

from __future__ import annotations

import logging
import threading
import time

import jwt
import requests
from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, login

logger = logging.getLogger(__name__)

TEAM_DOMAIN = "https://solitary-block-1911.cloudflareaccess.com"
CERTS_URL = f"{TEAM_DOMAIN}/cdn-cgi/access/certs"
JWT_HEADER = "HTTP_CF_ACCESS_JWT_ASSERTION"


class _KeyCache:
    """Cloudflare rotates signing keys, so these are fetched rather than pinned.

    Cached for an hour because a fetch on every request would make Cloudflare's availability a
    hard dependency of every page load. A fetch failure returns the previous keys if there are
    any, and otherwise returns nothing — which fails closed at the verification step.
    """

    TTL = 3600

    def __init__(self) -> None:
        self._keys: dict | None = None
        self._at = 0.0
        self._lock = threading.Lock()

    def get(self) -> dict | None:
        with self._lock:
            if self._keys is not None and time.time() - self._at < self.TTL:
                return self._keys
            try:
                # requests, not urlopen: urlopen accepts any scheme the stdlib knows,
                # including file://, which bandit flags as B310. A fair objection to the
                # call even though this URL is a hardcoded constant. requests is HTTP(S)
                # only, and is already a dependency here.
                r = requests.get(CERTS_URL, timeout=5)
                r.raise_for_status()
                self._keys = r.json()
                self._at = time.time()
            except Exception:
                logger.warning("Access: could not fetch signing keys", exc_info=True)
            return self._keys


_keys = _KeyCache()


def verify_access_token(token: str | None, audience: str | None = None) -> str | None:
    """Return the verified email, or None. Never raises into the request path."""
    audience = audience or getattr(settings, "CF_ACCESS_AUD", None)
    # Unset configuration fails closed. An app that silently stops checking because a variable is
    # missing is worse than one that refuses to log anybody in.
    if not token or not audience:
        return None

    jwks = _keys.get()
    if not jwks:
        return None

    try:
        header = jwt.get_unverified_header(token)
        key = next((k for k in jwks.get("keys", []) if k.get("kid") == header.get("kid")), None)
        if key is None:
            return None
        claims = jwt.decode(
            token,
            key=jwt.PyJWK.from_dict(key).key,
            algorithms=["RS256"],
            audience=audience,
            issuer=TEAM_DOMAIN,
            options={"require": ["exp", "iat", "sub", "email"]},
        )
    except Exception:
        # Expired, wrong audience, forged, malformed — all the same answer: not authenticated.
        return None

    if claims.get("type") != "app":
        return None
    return claims.get("email")


class CloudflareAccessMiddleware:
    """Log the verified Access identity into Django, once per session.

    Only the owner gets an account, and it is created with staff rights because every view here
    is ``@staff_member_required``. Anyone else who somehow reaches this code is left
    unauthenticated and meets the normal login page.

    Runs after AuthenticationMiddleware so ``request.user`` exists, and does nothing when a
    session is already signed in.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not getattr(request, "user", None) or not request.user.is_authenticated:
            email = verify_access_token(request.META.get(JWT_HEADER))
            owner = getattr(settings, "CF_ACCESS_OWNER_EMAIL", None)
            if email and owner and email == owner:
                user = authenticate(request, remote_user=email)
                if user is not None:
                    login(request, user)
        return self.get_response(request)


class OwnerOnlyRemoteUserBackend:
    """Resolve the verified email to the single owner account, creating it once.

    A thin backend rather than Django's RemoteUserBackend: that one creates an account for any
    name handed to it, which is correct behind a proxy that authenticates everyone but wrong for
    an app with exactly one legitimate user.
    """

    def authenticate(self, request, remote_user=None, **kwargs):
        owner = getattr(settings, "CF_ACCESS_OWNER_EMAIL", None)
        if not remote_user or not owner or remote_user != owner:
            return None
        User = get_user_model()
        user, created = User.objects.get_or_create(
            username=remote_user,
            defaults={"email": remote_user, "is_staff": True, "is_superuser": True},
        )
        if created:
            # No usable password: this account exists to be logged in by Access, and a blank or
            # guessable password on a superuser would undo the point of the exercise.
            user.set_unusable_password()
            user.save(update_fields=["password"])
            logger.info("Access: created owner account for %s", remote_user)
        return user

    def get_user(self, user_id):
        User = get_user_model()
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
