import base64
import binascii
import os
from pathlib import Path

import dj_database_url
from django.core.management.utils import get_random_secret_key

BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).lower() in {"1", "true", "yes", "on"}


DEBUG = env_bool("DJANGO_DEBUG")
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = get_random_secret_key()
    else:
        raise RuntimeError("DJANGO_SECRET_KEY must be set when DJANGO_DEBUG is false")
if not DEBUG and (
    len(SECRET_KEY) < 50
    or len(set(SECRET_KEY)) < 5
    or SECRET_KEY.startswith("django-insecure-")
):
    raise RuntimeError("DJANGO_SECRET_KEY is not strong enough for production")

allowed_hosts_raw = os.getenv(
    "DJANGO_ALLOWED_HOSTS", "" if not DEBUG else "localhost,127.0.0.1,[::1]"
)
ALLOWED_HOSTS = [
    host.strip()
    for host in allowed_hosts_raw.split(",")
    if host.strip()
]
if not DEBUG and (not ALLOWED_HOSTS or "*" in ALLOWED_HOSTS):
    raise RuntimeError("DJANGO_ALLOWED_HOSTS must be explicit in production")
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]
if not DEBUG and not CSRF_TRUSTED_ORIGINS:
    raise RuntimeError("DJANGO_CSRF_TRUSTED_ORIGINS must be set in production")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "stats",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "stats.middleware.SecurityHeadersMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "riot_api.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "stats.context_processors.application_settings",
            ],
        },
    }
]
WSGI_APPLICATION = "riot_api.wsgi.application"

database_url = os.getenv("DATABASE_URL", "")
if not DEBUG and not database_url.startswith(("postgres://", "postgresql://")):
    raise RuntimeError("DATABASE_URL must use PostgreSQL in production")
DATABASES = {
    "default": dj_database_url.config(
        default=database_url or f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=60,
        conn_health_checks=True,
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "America/Los_Angeles"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage"
            if DEBUG
            else "whitenoise.storage.CompressedManifestStaticFilesStorage"
        )
    },
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

RIOT_API_KEY = os.getenv("RIOT_API_KEY", "")
RIOT_API_KEY_ENCRYPTION_KEY = os.getenv("RIOT_API_KEY_ENCRYPTION_KEY", "")
if not DEBUG and not RIOT_API_KEY_ENCRYPTION_KEY:
    raise RuntimeError("RIOT_API_KEY_ENCRYPTION_KEY must be set when DJANGO_DEBUG is false")
if not DEBUG:
    try:
        decoded_credential_key = base64.b64decode(
            RIOT_API_KEY_ENCRYPTION_KEY, altchars=b"-_", validate=True
        )
    except (binascii.Error, ValueError) as exc:
        raise RuntimeError("RIOT_API_KEY_ENCRYPTION_KEY is invalid") from exc
    if len(decoded_credential_key) != 32:
        raise RuntimeError("RIOT_API_KEY_ENCRYPTION_KEY is invalid")
RIOT_DEFAULT_PLATFORM = os.getenv("RIOT_DEFAULT_PLATFORM", "na1")
RIOT_DEFAULT_ROUTING = os.getenv("RIOT_DEFAULT_ROUTING", "americas")
RIOT_MATCH_COUNT = max(1, min(int(os.getenv("RIOT_MATCH_COUNT", "20")), 100))
DPS_THREAT_THRESHOLD = float(os.getenv("DPS_THREAT_THRESHOLD", "1800"))

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True
SECURE_SSL_REDIRECT = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_AGE = 3600
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SECURE_HSTS_SECONDS = 31_536_000 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "no-referrer"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
DATA_UPLOAD_MAX_MEMORY_SIZE = 262_144
DATA_UPLOAD_MAX_NUMBER_FIELDS = 100
LOGIN_URL = "admin:login"
LOGIN_REDIRECT_URL = "api-settings"
