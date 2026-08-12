# Container and Cloud Run Handoff

Phase 6 packages the FastAPI-only simulator as a disposable container. It does
not deploy the service or move secrets. Supabase/Postgres remains authoritative;
the container contains only code, static frontend assets, and runtime Python
dependencies.

## Local image

Build from the repository root:

```powershell
docker build --pull --tag behavioral-credit-simulator:phase6 .
```

Run with an ignored runtime environment file:

```powershell
docker run --rm --name simulator-phase6 `
  --env-file .env.container `
  -e PORT=8080 `
  -p 8080:8080 `
  behavioral-credit-simulator:phase6
```

`PORT` defaults to `8080`, but the image command always reads it at container
startup and binds Uvicorn to `0.0.0.0`. The process uses `exec`, so Uvicorn is
PID 1 and receives Docker's SIGTERM directly. No reload mode or secondary
process manager is used.

Do not pass secrets as build arguments. Do not copy `.env` into the image. For
local verification, create an ignored `.env.container` containing only the
runtime values below. Keep `PROLIFIC_DYNAMIC_PAYMENT_ENABLED=false` and omit
`PROLIFIC_API_TOKEN` during non-payment acceptance testing.

## Runtime configuration contract

| Variable | Classification | Purpose | Required at startup/readiness | Current local source | Future Cloud Run source | Browser-safe |
|---|---|---|---|---|---|---|
| `SUPABASE_URL` | Required non-secret | Supabase project API URL | Yes | ignored `.env` | Cloud Run environment | No direct browser exposure |
| `SUPABASE_SECRET_KEY` | Required secret | Server-side Supabase credential | Yes | ignored `.env` | Secret Manager reference | No |
| `ACCOUNT_KEY_PEPPER` | Required secret | Stable opaque account-key derivation | Yes | ignored local env | Secret Manager reference | No |
| `BROWSER_SESSION_SECRET` | Required secret | Stable encrypted browser-session/OIDC-cookie key | Yes | ignored local env | Secret Manager reference | No |
| `PUBLIC_ORIGIN` | Required non-secret | Exact same-origin CSRF authority | Yes | ignored local env | Cloud Run environment | Yes |
| `GOOGLE_CLIENT_ID` | Required non-secret | Google OIDC audience/client | Yes | ignored local env | Cloud Run environment | Not returned by this app |
| `GOOGLE_CLIENT_SECRET` | Required secret | Google OIDC token exchange | Yes | ignored local env | Secret Manager reference | No |
| `GOOGLE_REDIRECT_URI` | Required non-secret | Exact OIDC callback URI | Yes | ignored local env | Cloud Run environment | Yes |
| `COOKIE_SECURE` | Required security config | Require HTTPS-only auth cookie | Image defaults `true` | local override may be `false` | Cloud Run environment: `true` | No need to expose |
| `ADMIN_EMAILS` | Optional feature config | Server-derived admin allowlist | Needed for admin access | ignored local env | Cloud Run environment or secret reference | No |
| `PROLIFIC_MODE_ENABLED` | Optional feature config | Enable validated Prolific launches | Explicitly configure | ignored local env | Cloud Run environment | No need to expose |
| `PROLIFIC_ALLOWED_STUDY_IDS` | Required when Prolific is enabled | Fail-closed launch allowlist | Conditional; readiness checks it | ignored local env | Cloud Run environment | No |
| `PROLIFIC_COMPLETION_CODE` | Optional/conditional config | Existing completion/payment lifecycle | Needed for configured completion | ignored local env | Secret Manager reference if treated as sensitive | No |
| `PROLIFIC_COMPLETION_URL` | Optional/conditional config | Safe participant completion destination template | Conditional | ignored local env | Cloud Run environment | Only the resolved safe URL may be projected |
| `PROLIFIC_INTEGRATION_URL` | Optional non-secret | Prolific request referer | Conditional | ignored local env | Cloud Run environment | No need to expose |
| `PROLIFIC_API_TOKEN` | Optional secret | Live Prolific transition credential | Only for live payment | ignored local env | Secret Manager reference | No |
| `PROLIFIC_DYNAMIC_PAYMENT_ENABLED` | Optional safety flag | Enables the existing live payment adapter when a token exists | No; keep `false` in acceptance tests | ignored local env | Cloud Run environment | No |
| `ALLOW_REPEAT_PARTICIPATION` | Development/controlled feature flag | Existing explicit repeat-participation override | No; defaults `false` | ignored local env | Cloud Run environment: normally `false` | No |
| `API_DOCS_ENABLED` | Optional operational config | FastAPI docs/OpenAPI exposure | No; image defaults `false` | local override | Cloud Run environment | N/A |
| `PORT` | Required container non-secret | HTTP listen port injected by Cloud Run | Container default `8080` | Docker runtime | Cloud Run injected | N/A |
| `FORWARDED_ALLOW_IPS` | Optional proxy trust config | Uvicorn forwarded-header trust boundary | No; defaults `127.0.0.1` | Docker runtime | Set only to the verified Cloud Run proxy boundary | N/A |

Compatibility aliases `SUPABASE_PROJECT_URL`, `SUPABASE_SERVICE_ROLE_KEY`, and
legacy `SUPABASE_KEY` remain accepted by the application. Prefer the canonical
names above. A publishable Supabase key is rejected for server persistence.

`SUPABASE_DB_URL`, `RUN_SUPABASE_INTEGRATION`, and
`SUPABASE_INTEGRATION_ALLOW_SYNTHETIC_WRITES` are integration-harness inputs,
not production container configuration, and are not passed to the application
container.

Missing core configuration does not crash the process: `/health` remains a
cheap liveness response while `/ready` returns `503`. `/ready` validates
configuration/composition without issuing a Supabase query.

## Health and smoke checks

After startup:

```powershell
Invoke-WebRequest http://localhost:8080/health
Invoke-WebRequest http://localhost:8080/ready
Invoke-WebRequest http://localhost:8080/
Invoke-WebRequest http://localhost:8080/admin
Invoke-WebRequest http://localhost:8080/static/js/app.js
```

An unauthenticated request to `/api/v1/sessions/{uuid}` must return `401`.
Startup/request logs include route, status, latency, and a request identifier;
they do not log request bodies, credentials, or participant identity payloads.

## Statelessness and horizontal-safety acceptance

Use a synthetic non-payment account and the real configured Supabase test
project. Never provide the Prolific token for this test.

The guarded harness automates the sequence after the integration environment
has been loaded and stable test-only browser/account secrets have been set:

```powershell
python scripts/verify_container_statelessness.py `
  --docker "C:\Program Files\Docker\Docker\resources\bin\docker.exe" `
  --image behavioral-credit-simulator:phase6 `
  --allow-synthetic-writes
```

It refuses to run unless both Phase 3.5 synthetic-write opt-ins equal `1`,
forces Prolific mode/payment off, uses unique container/session identifiers,
and deletes only the synthetic records it creates.

1. Start container A with stable `ACCOUNT_KEY_PEPPER` and
   `BROWSER_SESSION_SECRET` values.
2. Authenticate the controlled account, progress through server commands, and
   commit at least one month.
3. Record the safe state/version, then stop and remove A.
4. Start container B from the same image and external configuration without
   copying A's filesystem.
5. Reuse the browser cookie and load the owned session. Verify the version,
   stage/month, visible balances, committed feedback, and treatment-safe view.
6. Continue once and verify exactly one new durable transition.
7. Run A and B simultaneously on different host ports. Commit through A, read
   through B, send a stale version through B (expect `409`), retry the committed
   action through B with the same idempotency key (expect replay), and reuse that
   key with a different payload (expect `409`).

The encrypted browser cookie is portable across replacements only when
`BROWSER_SESSION_SECRET` remains stable. Rotating it logs browsers out but does
not alter durable experiment data. `ACCOUNT_KEY_PEPPER` must also remain stable;
rotating it breaks existing identity-to-account lookup.

## Image inspection checklist

```powershell
docker image inspect behavioral-credit-simulator:phase6
docker run --rm behavioral-credit-simulator:phase6 python --version
docker run --rm behavioral-credit-simulator:phase6 python -m pip list
docker run --rm --entrypoint sh behavioral-credit-simulator:phase6 -c "find /app -maxdepth 4 -type f -print"
```

The image must contain `requirements.txt`, the runtime `sim_app` modules, Python
runtime packages, and frontend assets. It must not contain `.env`, `.git`,
tests, in-memory test repositories, Playwright, browser binaries, caches, local
logs, SQL migration files, or attachment data.
The final user is UID/GID `10001`, and application source is root-owned/read-only
to that user.

## Google redirect preparation

Current local callback:

```text
http://localhost:8000/auth/google/callback
```

Future Cloud Run callback (configure only after a service URL exists):

```text
https://<cloud-run-host>/auth/google/callback
```

Future custom-domain callback, if used:

```text
https://<domain>/auth/google/callback
```

`PUBLIC_ORIGIN` and `GOOGLE_REDIRECT_URI` are runtime values. No Cloud Run host
is hardcoded in the image.

## Later Cloud Run deployment sequence (not performed in Phase 6)

1. Configure the Google Cloud project.
2. Enable the required Google services.
3. Create Secret Manager values and Cloud Run secret references.
4. Build and push this image to Artifact Registry.
5. Create the Cloud Run service.
6. Configure non-secret environment variables and secret references.
7. Deploy and obtain the Cloud Run HTTPS URL.
8. Register the exact Google OAuth callback and update runtime origin values.
9. Test Google login/logout and cookie/CSRF behavior.
10. Test Supabase readiness and a controlled participant journey.
11. Test the admin view with a server-authorized account.
12. Test an allowed Prolific launch with live payment disabled.
13. Optionally attach and validate a custom domain.
14. Only after full acceptance, decide when to retire the old hosting deployment
    and its still-untouched secrets.

Docker Compose, Cloud Run resources, Secret Manager changes, deployment YAML,
and live Prolific payment are intentionally outside Phase 6.
