# Browser Authentication Setup

The complete application is served by FastAPI. Google and Prolific identities are converted server-side into an opaque HMAC account key; neither the account key nor identity pepper is returned to browser JavaScript or stored beside research answers.

## Google OIDC

Create a Google OAuth Web application and configure this exact callback:

```text
https://<your-app-domain>/auth/google/callback
```

For local development, also allow:

```text
http://localhost:8000/auth/google/callback
```

Set these server environment variables:

```text
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_REDIRECT_URI=https://<your-app-domain>/auth/google/callback
ACCOUNT_KEY_PEPPER=<stable high-entropy secret>
BROWSER_SESSION_SECRET=<independent high-entropy secret>
PUBLIC_ORIGIN=https://<your-app-domain>
COOKIE_SECURE=true
ADMIN_EMAILS=admin@example.com
ALLOW_REPEAT_PARTICIPATION=false
```

The implementation uses authorization code flow, state, nonce, PKCE, signature/issuer/audience/expiry validation, and an encrypted HttpOnly browser cookie. State-changing JSON endpoints additionally require the cookie-bound CSRF token and a same-origin request.

Do not rotate `ACCOUNT_KEY_PEPPER` during data collection: doing so prevents existing-account recovery. Rotating `BROWSER_SESSION_SECRET` logs browsers out but does not alter durable participant identity.

## Prolific launches

Prolific should launch the same-origin application with the complete `PROLIFIC_PID`, `STUDY_ID`, and `SESSION_ID` query set. Browser code immediately sends that set to `/auth/prolific/launch`; the server uses `SESSION_ID` and the server-only Prolific API token to load the authoritative submission and compare all three identifiers. It also verifies that the authoritative study's external URL targets `PUBLIC_ORIGIN`, preventing a valid tuple from an unrelated study on the same researcher account from being reused. Only a matching tuple creates an HttpOnly authenticated session. The route then redirects to `/` so identifiers disappear from the visible URL.

Configure:

```text
PROLIFIC_API_TOKEN=...
PROLIFIC_COMPLETION_CODE=...
PROLIFIC_COMPLETION_URL=...
PROLIFIC_INTEGRATION_URL=https://<your-app-domain>/
```

When Prolific mode is enabled, a missing API token makes readiness and launch verification fail closed. The participant-provided identifiers are never trusted without the authoritative Prolific submission lookup.

At finalization the same token may create a calculated bonus batch for manual review. Active code never invokes the Prolific bonus `/pay/` operation and never completes a submission through a dynamic API transition. The completion URL/code handles the participant return. Automated tests use memory repositories and fakes and never invoke a live payment.

## Privacy and durable recovery

In-progress ownership remains in `resume_links`. Finalization stores the opaque account key in `completed_accounts` and removes the resume row. The encrypted browser session binds the finalized session ID long enough to recover a lost finalization response without exposing the account key or recreating a resume link.
