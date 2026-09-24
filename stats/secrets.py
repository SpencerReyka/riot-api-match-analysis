import logging
from dataclasses import dataclass
from datetime import datetime

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.db import OperationalError, ProgrammingError, transaction
from django.views.decorators.debug import sensitive_variables

from .models import ApplicationSecret

logger = logging.getLogger(__name__)


class SecretStorageError(RuntimeError):
    """Raised when an application credential cannot be safely stored or read."""


@dataclass(frozen=True)
class SecretStatus:
    configured: bool
    source: str
    updated_at: datetime | None = None
    updated_by: str = ""
    storage_error: bool = False


def _cipher() -> Fernet:
    raw_key = settings.RIOT_API_KEY_ENCRYPTION_KEY
    if not raw_key:
        raise SecretStorageError("The credential encryption key is not configured.")
    try:
        return Fernet(raw_key.encode("ascii"))
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise SecretStorageError("The credential encryption key is invalid.") from exc


def _stored_secret() -> ApplicationSecret | None:
    try:
        return ApplicationSecret.objects.filter(
            name=ApplicationSecret.RIOT_API_KEY
        ).first()
    except (OperationalError, ProgrammingError):
        # This permits initial migrations and disaster recovery before the table exists.
        return None


def get_riot_api_key() -> str:
    stored = _stored_secret()
    if stored is None:
        return settings.RIOT_API_KEY
    try:
        plaintext = _cipher().decrypt(stored.encrypted_value.encode("ascii")).decode(
            "utf-8"
        )
    except (InvalidToken, UnicodeDecodeError, UnicodeEncodeError, ValueError) as exc:
        raise SecretStorageError("The stored Riot credential cannot be decrypted.") from exc
    if not plaintext:
        raise SecretStorageError("The stored Riot credential is empty.")
    return plaintext


@transaction.atomic
@sensitive_variables("api_key", "value", "encrypted")
def set_riot_api_key(api_key: str, *, updated_by: str = "") -> None:
    value = api_key.strip()
    if not value.startswith("RGAPI-"):
        raise SecretStorageError("The Riot credential has an invalid format.")
    encrypted = _cipher().encrypt(value.encode("utf-8")).decode("ascii")
    ApplicationSecret.objects.update_or_create(
        name=ApplicationSecret.RIOT_API_KEY,
        defaults={
            "encrypted_value": encrypted,
            "updated_by": updated_by[:150],
        },
    )
    logger.info("Riot API credential replaced by a staff user")


def riot_api_key_status() -> SecretStatus:
    stored = _stored_secret()
    if stored is None:
        return SecretStatus(bool(settings.RIOT_API_KEY), "environment")
    try:
        configured = bool(get_riot_api_key())
    except SecretStorageError:
        return SecretStatus(
            False,
            "database",
            stored.updated_at,
            stored.updated_by,
            storage_error=True,
        )
    return SecretStatus(
        configured,
        "database",
        stored.updated_at,
        stored.updated_by,
    )
