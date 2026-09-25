# Revival TODO

Last updated: 2026-09-25

This is the working checklist for bringing `riot-api-match-analysis` back into service as a
private application at `riot.spencerreyka.com`.

## Application

- [x] Start the revival from `main` while preserving the old `development` branch for history.
- [x] Replace Summoner Name lookup with Riot ID (`gameName` + `tagLine`) and PUUID.
- [x] Send `RIOT_API_KEY` in the `X-Riot-Token` header.
- [x] Request ARAM queue 450 directly.
- [x] Add bounded timeouts, retry handling, and `Retry-After` support.
- [x] Replace the handwritten PostgreSQL layer with Django models and transactions.
- [x] Cache matches and relink cached participants when another tracked player is added.
- [x] Preserve the original 1,800 damage-per-minute threat calculation as configuration.
- [x] Add a server-rendered dashboard and per-player match history.
- [x] Show a useful setup state when the Riot key is absent.
- [x] Add staff-only API key validation and encrypted database-backed rotation.
- [x] Finish responsive styling and accessibility review.
- [x] Add the initial Django migration and verify a clean database bootstrap.
- [x] Add a management command for noninteractive account synchronization.

## Tests and packaging

- [x] Cover Riot ID lookup, header authentication, ARAM filtering, retries, and error mapping.
- [x] Cover match caching, participant extraction, analysis, and cached-match reuse.
- [x] Cover dashboard, form errors, refresh behavior, authorization, key rotation, and health checks.
- [x] Add a non-root production Docker image and health check.
- [x] Add local Docker Compose with PostgreSQL.
- [x] Add GitHub Actions for tests, Django deployment checks, and container builds.
- [x] Run dependency and container vulnerability scans.

## Security and repository maintenance

- [x] Keep production debug mode disabled and require production signing and credential-encryption keys.
- [x] Confirm secure proxy, CSRF, cookie, host, static-file, and browser security-header settings.
- [x] Remove the expired Riot key from public Git history or document the accepted historical risk.
- [x] Enable GitHub dependency, secret, and extended CodeQL scanning where repository settings allow it.
- [x] Replace the unfinished README with current local, deployment, and recovery instructions.
- [x] Preserve the divergent `development` branch intentionally as historical implementation context.

## Infrastructure

- [x] Register `riot-match-analysis` in `infra/services.yml` with access, health, backup, and secrets.
- [x] Add `riot.spencerreyka.com` to the Coolify VM Cloudflare tunnel.
- [x] Create a Spencer-only Cloudflare Access application and policy.
- [x] Create a Coolify Git application with a 256 MB memory limit and 96 MB reservation.
- [x] Create a dedicated PostgreSQL resource with a 256 MB memory limit.
- [x] Add the application database to the encrypted ops backup and restore runbook.
- [x] Add internal and external health monitoring through Uptime Kuma.
- [x] Regenerate the infrastructure inventory and pass drift checks.

## Deployment

- [x] Store `DJANGO_SECRET_KEY`, database credentials, and `RIOT_API_KEY` through the established SOPS/Coolify workflow.
- [x] Configure the signed GitHub-to-Coolify deployment webhook.
- [x] Deploy and apply migrations.
- [x] Verify Cloudflare Access, health, resource limits, database persistence, and backup coverage.
- [x] Validate a real Riot ID import and cached repeat import.

## External dependency

- [x] Add the current Riot personal API key to the encrypted SOPS source of truth. Development
      keys expire every 24 hours, so live imports require refreshing this value when it expires;
      the deployed service can continue displaying cached data without a current key.

## Public request queue

- [x] Add a public landing page and opaque per-request status/result URLs.
- [x] Persist the request and `riot.analysis.requested` protobuf outbox event atomically.
- [x] Add an idempotent RabbitMQ worker with publisher confirms, delayed retries, and a DLQ.
- [x] Add database-backed visitor limits, Riot-ID cooldown, and a bounded global queue.
- [x] Add a shared database-backed Riot API budget below the documented upstream limits.
- [x] Require an explicit production-key tier before anonymous submission can start.
- [ ] Obtain and install an approved Riot production key.
- [ ] Provision the worker as a separate Coolify process with the Backbone AMQP secret.
- [ ] Change Cloudflare Access from whole-host coverage to staff paths only, leaving the landing,
      request POST, and opaque result URLs public.
- [ ] Extend the existing Free-plan Cloudflare rate-limit rule to the public submission path and
      verify the WAF, queue ceiling, worker health, retry queue, and DLQ in production.
