# Riot API match analysis

A Django service that accepts bounded Riot-ID analysis requests, caches ARAM matches, and
highlights games in which the tracked player exceeded the configured damage-per-minute threshold.

The production hostname is `riot.spencerreyka.com`. The public request UI, event worker, and
rate-limit controls are implemented, but anonymous submissions remain disabled and the hostname
remains behind Cloudflare Access until an approved Riot production key is installed. Staff
dashboard, manual refresh, Django admin, and API-key rotation always require the verified owner.

## Request architecture

Submitting a Riot ID writes an `AnalysisRequest` and a protobuf `riot.analysis.requested` event to
the PostgreSQL outbox in the same transaction. The worker confirms publication to the durable
Backbone RabbitMQ exchange, consumes from its own durable queue, and processes the request
idempotently. Broker downtime leaves the outbox intact; a crash after publication may create a
duplicate delivery, which the worker safely ignores after completion.

Protection is layered:

- three submissions per 10 minutes and ten per day for a hashed visitor IP;
- a 15-minute per-Riot-ID deduplication window and a global 100-job queue ceiling;
- one worker delivery at a time with bounded delayed retry and a dead-letter queue;
- a shared PostgreSQL Riot budget of 15 requests/second and 80 requests/two minutes, below the
  personal-key ceilings, plus Riot's `Retry-After` response handling;
- Cloudflare WAF/rate limiting at the edge before anonymous access is enabled.

## Local development

Python 3.14 is recommended to match the production container and CI runtime.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
DJANGO_DEBUG=true .venv/bin/python manage.py migrate
DJANGO_DEBUG=true .venv/bin/python manage.py runserver
```

The local default is SQLite. To run the production-shaped app and PostgreSQL together:

```bash
cp .env.example .env
# Set POSTGRES_PASSWORD and DATABASE_URL in .env, then:
docker compose up --build
```

Open `http://127.0.0.1:8000`. Create a local administrator with:

```bash
docker compose exec app python manage.py createsuperuser
```

Synchronize explicit Riot IDs or refresh every tracked account without the browser:

```bash
docker compose exec app python manage.py sync_accounts 'Game Name#NA1'
docker compose exec app python manage.py sync_accounts --all
```

Run the event worker against an existing Backbone broker:

```bash
docker compose --profile worker up --build
```

The canonical protobuf schema lives in the `backbone` repository. Python bindings in
`stats/generated/` are generated artifacts from `backbone/v1/envelope.proto` and
`backbone/v1/events/riot.proto`.

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
| `RIOT_API_KEY_TIER` | `development`, `personal`, or `production`; anonymous requests require `production` |
| `RIOT_PUBLIC_REQUESTS_ENABLED` | Enables anonymous submission only when the production-key guard passes |
| `BACKBONE_RABBITMQ_URL` | Internal AMQP URL used by the outbox relay/analysis worker |
| `PUBLIC_REQUESTS_PER_10_MINUTES` / `PUBLIC_REQUESTS_PER_DAY` | Per-visitor submission ceilings |
| `PUBLIC_REQUEST_COOLDOWN_SECONDS` | Per-Riot-ID deduplication window, default 900 |
| `PUBLIC_REQUEST_QUEUE_LIMIT` | Maximum queued/processing jobs, default 100 |
| `RIOT_REQUESTS_PER_SECOND` / `RIOT_REQUESTS_PER_2_MINUTES` | Shared upstream budgets, defaults 15/80 |

Production secrets belong in the infra repository's SOPS workflow, never in this repository.

## Production image

The image runs as uid/gid `10001`, exposes port 8000, and contains a database-aware health
check. Its entrypoint collects static files and applies migrations before starting Gunicorn.

```bash
docker build -t riot-match-analysis .
```

Production needs PostgreSQL and all required environment variables before the container starts.
Set `APP_PROCESS=worker` to run the Backbone relay/consumer instead of Gunicorn. The image has a
process-aware health check. It deliberately fails closed when a signing key, encryption key,
allowed host, trusted origin, or PostgreSQL URL is missing, and refuses to enable anonymous
requests without a production key tier. The worker command separately refuses to start without
its broker URL.

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
