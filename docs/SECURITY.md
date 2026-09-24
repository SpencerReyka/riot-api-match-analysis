# Security review

Last reviewed: 2026-09-23

This review covers the Django application and its Cloudflare/Coolify boundary. DNS, Access, and
the Tunnel route are live; the application and database deployment remain pending.

## Trust model

- The entire hostname is private behind a Spencer-only Cloudflare Access policy while the app
  uses a development or personal Riot key. Visitors who pass Access can read cached dashboards
  without also starting a Django session.
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
- Production requires `DEBUG=false`, a non-default `DJANGO_SECRET_KEY`, HTTPS redirects, secure
  cookies, one-hour browser-session expiry, HSTS, strict host validation, and an explicit trusted
  CSRF origin.
- Non-admin pages allow no script execution and load no third-party fonts. CSP, Permissions Policy,
  frame denial, no-referrer, MIME-sniffing prevention, COOP, and same-origin resource policy are
  applied centrally.
- The public health response reports database availability only; it does not disclose credential
  state.
- The legacy plaintext `config.txt` loader was removed from `manage.py`.

## Cloudflare deployment status

Verified on 2026-09-23:

1. `riot.spencerreyka.com` is a proxied CNAME to the Coolify VM Cloudflare Tunnel; the tracked
   tunnel route targets `127.0.0.1:3230`. Do not open port 3230 in the VM NSG or attach a public
   origin IP.
2. The entire hostname is covered by an eight-hour Access application that uses the Google
   identity provider and allows only `spencer.reyka@gmail.com`. It has no public bypass.
3. Binding and HttpOnly cookies are enabled. The app is hidden from the Access launcher, and an
   unauthenticated request was verified to redirect to Access.

Still required:

1. Enable Cloudflare managed WAF rules. Rate-limit POST requests to `/admin/login/`, `/accounts/`,
   `/accounts/*/refresh/`, and `/settings/riot-api/`. A reasonable starting point is five login
   attempts per minute per IP and ten application mutations per minute per authenticated user/IP.
   The current API token lacks Zone Rulesets permission, so this cannot be provisioned with the
   available credential.
2. Give external monitoring an Access service token for `/healthz`; do not create a public bypass.
3. Set production values exactly: `DJANGO_ALLOWED_HOSTS=riot.spencerreyka.com` and
   `DJANGO_CSRF_TRUSTED_ORIGINS=https://riot.spencerreyka.com`.
4. Create the Django superuser interactively in the Coolify terminal with a unique password. Do
   not keep an initial admin password in SOPS or a persistent environment variable.

## Remaining findings before deployment

| Severity | Finding | Required closure |
|---|---|---|
| High | Managed-WAF and application rate-limit rules are not provisioned because the current Cloudflare token lacks Zone Rulesets permission. | Supply a narrowly scoped Rulesets token, apply the rules, and verify them before deploying the app. |
| High | PostgreSQL and encrypted backup/restore are not yet provisioned. | Test restore of the database together with the SOPS encryption key. |
| High | Riot forbids public consumption with development or personal keys. | Keep the whole hostname Access-gated, or obtain a production key before allowing public access. |
| Medium | The dashboard displays Riot IDs and match-derived statistics to Access-authorized viewers. | Keep the Access allowlist limited to intended viewers. |
| Medium | Django does not natively throttle login attempts. | Treat Cloudflare Access and login rate limiting as required, not optional. |
| Medium | GitHub secret scanning, push protection, Dependabot alerts, and security updates are disabled. | Enable them in repository settings before merging the deployment branch. |
| Medium | Dependency and container scanning are not yet automated. | Add CI auditing and fail builds on actionable high/critical findings. |
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

- [Django deployment checklist](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/)
- [Django security guidance](https://docs.djangoproject.com/en/5.2/topics/security/)
- [Cloudflare proactive DDoS defense](https://developers.cloudflare.com/ddos-protection/best-practices/proactive-defense/)
- [Cloudflare Access application paths](https://developers.cloudflare.com/cloudflare-one/access-controls/policies/app-paths/)
- [Riot Developer Portal key types and security](https://developer.riotgames.com/docs/portal)
