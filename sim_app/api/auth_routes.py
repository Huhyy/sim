"""Same-origin Google OIDC and Prolific browser-session routes."""

from __future__ import annotations

from dataclasses import replace

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse, RedirectResponse

from sim_app.api.dependencies import get_browser_session_manager, get_principal, get_service, require_csrf
from sim_app.application.errors import AuthenticationRequired, ProlificLaunchError
from sim_app.application.principal import ParticipantPrincipal
from sim_app.auth.admin import is_admin_email
from sim_app.auth.browser_session import OIDC_COOKIE, SESSION_COOKIE
from sim_app.auth.identity import derive_account_key, derive_prolific_account_key
from sim_app.auth.oidc import GoogleOidcClient
from sim_app.config import PROLIFIC_MODE_ENABLED
from sim_app.content.translations import get_ui_section
from sim_app.prolific.identity import normalize_prolific_params, prolific_params_complete, prolific_study_allowed


router = APIRouter()


@router.get("/api/v1/public/content/{language}")
def public_content(language: str):
    selected = language if language in {"en", "ro"} else "en"
    return {
        "auth": get_ui_section("auth", selected),
        "already_completed": get_ui_section("already_completed", selected),
        "prolific": get_ui_section("prolific", selected),
    }


def _prolific_launch_failure(request: Request, code: str, message: str):
    if "text/html" in request.headers.get("Accept", ""):
        return RedirectResponse(f"/?prolific_error={code}", status_code=303)
    raise ProlificLaunchError(message)


def _oidc_client(request):
    provider = getattr(request.app.state, "oidc_client", None)
    if provider is None:
        provider = GoogleOidcClient()
        request.app.state.oidc_client = provider
    return provider


@router.get("/auth/google/login")
def google_login(request: Request):
    manager = get_browser_session_manager(request)
    url, transaction = _oidc_client(request).begin()
    response = RedirectResponse(url, status_code=302)
    response.set_cookie(
        OIDC_COOKIE,
        manager.encode_oidc_transaction(transaction),
        max_age=600,
        httponly=True,
        secure=manager.secure,
        samesite="lax",
        path="/auth/google/callback",
    )
    return response


@router.get("/auth/google/callback")
def google_callback(request: Request, code: str = Query(min_length=1), state: str = Query(min_length=1)):
    manager = get_browser_session_manager(request)
    transaction = manager.decode_oidc_transaction(request.cookies.get(OIDC_COOKIE))
    try:
        claims = _oidc_client(request).complete(code=code, state=state, transaction=transaction)
    except Exception as exc:
        raise AuthenticationRequired("Google authentication could not be verified") from exc
    if claims.get("email_verified") is not True:
        raise AuthenticationRequired("Google did not verify the account email address")
    email = str(claims["email"]).strip().lower()
    principal = ParticipantPrincipal(
        account_key=derive_account_key(issuer=str(claims["iss"]), subject=str(claims["sub"])),
        identity_kind="google",
        email=email,
        display_name=str(claims.get("name") or email),
        is_admin=is_admin_email(email),
    )
    response = RedirectResponse("/", status_code=303)
    manager.set_principal_cookie(response, principal)
    response.delete_cookie(OIDC_COOKIE, path="/auth/google/callback", httponly=True, secure=manager.secure, samesite="lax")
    return response


@router.get("/auth/prolific/launch")
def prolific_launch(
    request: Request,
    prolific_pid: str | None = Query(None, alias="PROLIFIC_PID"),
    study_id: str | None = Query(None, alias="STUDY_ID"),
    prolific_session_id: str | None = Query(None, alias="SESSION_ID"),
    service=Depends(get_service),
):
    if not PROLIFIC_MODE_ENABLED:
        return _prolific_launch_failure(request, "invalid_study", "Prolific participation is not enabled")
    params = normalize_prolific_params({
        "PROLIFIC_PID": prolific_pid,
        "STUDY_ID": study_id,
        "SESSION_ID": prolific_session_id,
    })
    if not prolific_params_complete(params):
        return _prolific_launch_failure(
            request,
            "missing_params",
            "A complete Prolific launch parameter set is required",
        )
    if not prolific_study_allowed(params["STUDY_ID"]):
        return _prolific_launch_failure(request, "invalid_study", "This Prolific study is not enabled")
    principal = ParticipantPrincipal(
        account_key=derive_prolific_account_key(
            prolific_pid=params["PROLIFIC_PID"],
            study_id=params["STUDY_ID"],
        ),
        identity_kind="prolific",
        prolific_pid=params["PROLIFIC_PID"],
        prolific_study_id=params["STUDY_ID"],
        prolific_session_id=params["SESSION_ID"],
        display_name="Prolific participant",
    )
    try:
        existing_id = service.find_prolific_owned_session_id(principal)
    except ProlificLaunchError as exc:
        return _prolific_launch_failure(request, "already_completed", str(exc))
    if existing_id:
        principal = replace(principal, bound_session_id=existing_id)
    response = RedirectResponse("/", status_code=303)
    get_browser_session_manager(request).set_principal_cookie(response, principal)
    return response


@router.get("/api/v1/auth/session")
def auth_session(request: Request, principal=Depends(get_principal)):
    manager = get_browser_session_manager(request)
    _decoded, csrf_token = manager.decode_principal(request.cookies.get(SESSION_COOKIE))
    return {
        "authenticated": True,
        "identity_kind": principal.identity_kind,
        "display_name": principal.display_name,
        "email": principal.email,
        "is_admin": principal.is_admin,
        "session_id": principal.bound_session_id,
        "csrf_token": csrf_token,
    }


@router.post("/api/v1/auth/logout", dependencies=[Depends(require_csrf)])
def logout(request: Request):
    response = JSONResponse({"logged_out": True})
    get_browser_session_manager(request).clear_principal_cookie(response)
    return response


__all__ = ["router"]
