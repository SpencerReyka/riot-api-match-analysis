# Revival TODO

Last updated: 2026-09-23

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
- [ ] Finish responsive styling and accessibility review.
- [x] Add the initial Django migration and verify a clean database bootstrap.
- [ ] Add a management command for noninteractive account synchronization.

## Tests and packaging

- [x] Cover Riot ID lookup, header authentication, ARAM filtering, retries, and error mapping.
- [x] Cover match caching, participant extraction, analysis, and cached-match reuse.
- [x] Cover dashboard, form errors, refresh behavior, authorization, key rotation, and health checks.
- [ ] Add a non-root production Docker image and health check.
- [ ] Add local Docker Compose with PostgreSQL.
- [ ] Add GitHub Actions for tests, Django deployment checks, and container builds.
- [ ] Run dependency and container vulnerability scans.

## Security and repository maintenance

- [x] Keep production debug mode disabled and require production signing and credential-encryption keys.
- [x] Confirm secure proxy, CSRF, cookie, host, static-file, and browser security-header settings.
- [x] Remove the expired Riot key from public Git history or document the accepted historical risk.
- [ ] Enable GitHub dependency and secret scanning where repository settings allow it.
- [ ] Replace the unfinished README with current local, deployment, and recovery instructions.
- [ ] Review and either close or preserve the divergent `development` branch intentionally.

## Infrastructure

- [x] Register `riot-match-analysis` in `infra/services.yml` with access, health, backup, and secrets.
- [x] Add `riot.spencerreyka.com` to the Coolify VM Cloudflare tunnel.
- [x] Create a Spencer-only Cloudflare Access application and policy.
- [ ] Create a Coolify Git application with a 256 MB memory limit and 96 MB reservation.
- [ ] Create a dedicated PostgreSQL resource with a 256 MB memory limit.
- [ ] Add the application database to the encrypted ops backup and restore runbook.
- [ ] Add internal and external health monitoring through Uptime Kuma.
- [x] Regenerate the infrastructure inventory and pass drift checks.

## Deployment

- [ ] Store `DJANGO_SECRET_KEY`, database credentials, and `RIOT_API_KEY` through the established SOPS/Coolify workflow.
- [ ] Configure the signed GitHub-to-Coolify deployment webhook.
- [ ] Deploy and apply migrations.
- [ ] Verify Cloudflare Access, health, resource limits, database persistence, and backup coverage.
- [ ] Validate a real Riot ID import and cached repeat import.

## External dependency

- [x] Add the current Riot personal API key to the encrypted SOPS source of truth. Development
      keys expire every 24 hours, so live imports require refreshing this value when it expires;
      the deployed service can continue displaying cached data without a current key.
