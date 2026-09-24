# Riot API match analysis

A private Django dashboard that imports Riot IDs, caches ARAM matches, and highlights losses in
which the tracked player exceeded the configured damage-per-minute threshold.

The production hostname is `riot.spencerreyka.com`. Cloudflare Access protects the entire
hostname; imports, refreshes, Django admin, and Riot API-key rotation additionally require a
Django staff account.

## Local development

Python 3.13+ is recommended.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
DJANGO_DEBUG=true .venv/bin/python manage.py migrate
DJANGO_DEBUG=true .venv/bin/python manage.py runserver
```

The local default is SQLite. To run the production-shaped app and PostgreSQL together:

```bash
cp .env.example .env
# Set POSTGRES_PASSWORD in .env, then:
docker compose up --build
```

Open `http://127.0.0.1:8000`. Create a local administrator with:

```bash
docker compose exec app python manage.py createsuperuser
```

## Configuration

| Variable | Purpose |
|---|---|
| `DJANGO_DEBUG` | Development mode; must be false or absent in production |
| `DJANGO_SECRET_KEY` | Django signing key; required in production |
| `DJANGO_ALLOWED_HOSTS` | Explicit comma-separated hosts |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Explicit HTTPS origins |
| `DATABASE_URL` | PostgreSQL URL in production |
| `RIOT_API_KEY` | Bootstrap/recovery Riot credential; the encrypted database override wins |
| `RIOT_API_KEY_ENCRYPTION_KEY` | Fernet key protecting the database credential |
| `RIOT_DEFAULT_PLATFORM` | Riot platform region, default `na1` |
| `RIOT_DEFAULT_ROUTING` | Riot routing region, default `americas` |
| `RIOT_MATCH_COUNT` | Matches requested per synchronization, 1–100 |
| `DPS_THREAT_THRESHOLD` | Damage-per-minute threat threshold, default `1800` |

Production secrets belong in the infra repository's SOPS workflow, never in this repository.

## Production image

The image runs as uid/gid `10001`, exposes port 8000, and contains a database-aware health
check. Its entrypoint collects static files and applies migrations before starting Gunicorn.

```bash
docker build -t riot-match-analysis .
```

Production needs PostgreSQL and all required environment variables before the container starts.
The image deliberately fails closed when a signing key, encryption key, allowed host, trusted
origin, or PostgreSQL URL is missing.

## Tests and security checks

```bash
DJANGO_DEBUG=true .venv/bin/python manage.py test
DJANGO_DEBUG=true .venv/bin/python manage.py makemigrations --check --dry-run
.venv/bin/bandit -q -r manage.py riot_api stats
.venv/bin/pip-audit -r requirements.txt
```

CI repeats these checks, validates Django's production configuration, builds the image, and fails
on actionable high or critical container findings. Dependabot covers Python, Docker, and GitHub
Actions dependencies.

See [the revival checklist](docs/TODO.md) and [security review](docs/SECURITY.md) for deployment,
recovery, and accepted-risk details.
