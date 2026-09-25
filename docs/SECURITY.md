# Security review

Last reviewed: 2026-09-25

This review covers the Django application and its Cloudflare/Coolify boundary. DNS, Access, and
the Tunnel route are live. The application and its private PostgreSQL database run in Coolify.

## Trust model

- The entire hostname is private behind a Spencer-only Cloudflare Access policy while the app
  uses a development or personal Riot key. Visitors who pass Access can read cached dashboards
  without also starting a Django session.
- Anonymous submission code is present but fails closed unless both
  `RIOT_PUBLIC_REQUESTS_ENABLED=true` and `RIOT_API_KEY_TIER=production` are configured. The
  worker separately requires an internal Backbone RabbitMQ URL.
- Import, refresh, credential rotation, and Django admin operations require an active staff user.
- Cloudflare proxies all browser traffic. The origin must remain unreachable from the public
  Internet except through the existing Cloudflare Tunnel.
- Django staff authentication is an additional check for imports, refreshes, `/admin*`, and
  `/settings*`. An edge-policy mistake must not expose a privileged action.

## Implemented application controls

- Riot credential updates are accepted only on the staff-protected settings page and are checked
  against Riot before storage.
- The database stores Fernet ciphertext, never the Riot token. Its independent encryption key is
  held in SOPS and is required when production settings load.
- A database credential overrides the SOPS-provided Riot token. The environment value remains a
  recovery/bootstrap fallback and is never rendered.
- The key field uses a password input, is never pre-populated, and is not registered in Django
  admin. Logs record only that a staff user rotated it.
- Public users cannot call import or refresh POST endpoints. CSRF middleware remains enabled and
  every mutating form includes a CSRF token.
- Public requests use an unguessable UUID, never expose the internal account id, and are
  protected by hashed-IP fixed-window limits, per-Riot-ID deduplication, a bounded queue, a form
  honeypot, and no-store responses. Raw visitor IP addresses are not persisted.
- The request and protobuf outbox envelope commit atomically. RabbitMQ publication uses confirms,
  the durable consumer is idempotent, transient failures have bounded delayed retries, and
  exhausted or malformed events enter a DLQ.
- A PostgreSQL-coordinated limiter keeps all web and worker processes at 15 calls/second and 80
  calls/two minutes per Riot routing region by default. Riot 429 responses still honor
  `Retry-After`.
- Production requires `DEBUG=false`, a non-default `DJANGO_SECRET_KEY`, HTTPS redirects, secure
  cookies, one-hour browser-session expiry, HSTS, strict host validation, and an explicit trusted
  CSRF origin.
- Non-admin pages allow no script execution and load no third-party fonts. CSP, Permissions Policy,
  frame denial, no-referrer, MIME-sniffing prevention, COOP, and same-origin resource policy are
  applied centrally.
- The public health response reports database availability only; it does not disclose credential
  state.
- The legacy plaintext `config.txt` loader was removed from `manage.py`.
- The production container runs as uid/gid 10001, has an in-image database-aware health check,
  and contains no package installer or unused Python build tooling.
- CI runs tests, migration and deployment checks, Bandit, `pip-audit`, an image build, and Trivy.
- GitHub CodeQL default setup scans Python and Actions weekly with the extended query suite.
  The deployed image passed with no high or critical findings.

## Cloudflare deployment status

Verified on 2026-09-23:

1. `riot.spencerreyka.com` is a proxied CNAME to the Coolify VM Cloudflare Tunnel; the tracked
   tunnel route targets `127.0.0.1:3230`. Do not open port 3230 in the VM NSG or attach a public
   origin IP.
2. The entire hostname is covered by an eight-hour Access application that uses the Google
   identity provider and allows only `spencer.reyka@gmail.com`. It has no public bypass.
3. Binding and HttpOnly cookies are enabled. The app is hidden from the Access launcher, and an
   unauthenticated request was verified to redirect to Access.

Also verified on 2026-09-24:

1. A separate, more-specific `/healthz` Access application accepts only a one-year service token.
   It returns the real Django/PostgreSQL health response without creating a public bypass.
2. Production uses the exact host and trusted origin values above. Coolify holds runtime values
   sourced from SOPS, and the database has no public port.
3. The signed GitHub webhook, 256 MB application and database limits, migrations, health check,
   encrypted backup, checksum, decryption, and `pg_restore --list` validation were verified.
4. Uptime Kuma contains both the Access-edge and authenticated application/database health
   monitors. A real Riot ID sync imported an ARAM match, and an immediate repeat reused it from
   the database cache without inserting another match.
5. Cloudflare's Free Managed Ruleset is deployed. A zone-level path rule limits the login,
   account mutation/refresh, and API-key settings endpoints to four requests per 10 seconds per
   IP, followed by a 10-second block.

Still required:

1. Create the Django superuser interactively in the Coolify terminal with a unique password. Do
   not keep an initial admin password in SOPS or a persistent environment variable.

## Remaining findings

| Severity | Finding | Required closure |
|---|---|---|
| High | Riot forbids public consumption with development or personal keys. | The application now enforces this boundary in configuration. Keep the whole hostname Access-gated until an approved production key is installed, then explicitly enable requests. |
| Medium | The dashboard displays Riot IDs and match-derived statistics to Access-authorized viewers. | Keep the Access allowlist limited to intended viewers. |
| Medium | Application limits cannot absorb a volumetric attack before it reaches the origin. | Keep Cloudflare proxying/WAF enabled and extend the edge rate-limit expression to `/requests/` before public cutover. |
| Low | A database dump reveals update timestamps and ciphertext. | Expected; keep the Fernet key separate and restrict backup access. |

## Historical secret decision

History scanning found the expired development key already documented by commits `509d841` and
`25d8a47`, in `example_config.txt`. Riot development keys expire after 24 hours and the current
key is not present in tracked files. Rewriting the public repository would invalidate clones and
branches without reducing access to a usable credential, so the expired value is accepted as
historical residue. Any active or long-lived credential found in history must instead be revoked
and the history-removal decision revisited.

## Rotation and recovery

- Rotate an expired Riot development key through the staff settings page. Do not paste it into
  logs, tickets, shell arguments, or chat after rotation.
- Rotating `RIOT_API_KEY_ENCRYPTION_KEY` requires decrypting and re-encrypting the stored value in
  one controlled operation. Replacing the master key alone intentionally makes the row unusable.
- A database restore needs the matching SOPS-held encryption key. Test the pair together.
- If staff authentication or encrypted storage is unavailable, update the SOPS fallback and
  redeploy; do not introduce a plaintext recovery file.

## References

- [Django deployment checklist](https://docs.djangoproject.com/en/6.1/howto/deployment/checklist/)
- [Django security guidance](https://docs.djangoproject.com/en/6.1/topics/security/)
- [Cloudflare proactive DDoS defense](https://developers.cloudflare.com/ddos-protection/best-practices/proactive-defense/)
- [Cloudflare Access application paths](https://developers.cloudflare.com/cloudflare-one/access-controls/policies/app-paths/)
- [Riot Developer Portal key types and security](https://developer.riotgames.com/docs/portal)
