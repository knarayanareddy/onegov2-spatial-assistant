"""Authentication (Phase 6) — configurable, accountability-grade.

AUTH_MODE:
  - "dev"    : a single local user (default; unchanged behaviour, admin role) — no IdP needed.
  - "jwt"    : verify a Bearer token (HS256 shared secret, or RS256 via a JWKS URL).
  - "header" : trust an OIDC reverse-proxy identity header (e.g. X-Auth-User).

`get_current_user` is a FastAPI dependency. Adds roles + `require_role` (so FAQ
moderation can be admin-only) and an `AUTH_REQUIRED` gate. The sandbox has no live
IdP, so the jwt path is verified with a minted token; pointing it at the province's
real SSO is environment config. Default (dev) keeps everything working as today.
"""
from fastapi import Depends, HTTPException, Request
from pydantic import BaseModel

from app.config import settings
from app.models.session import Session


class CurrentUser(BaseModel):
    oid: str
    name: str
    email: str | None = None
    roles: list[str] = []
    auth_mode: str = "dev"


def _dev_user() -> CurrentUser:
    # Dev keeps the admin role so single-user moderation works as before.
    return CurrentUser(oid="local-user", name="Local User", roles=[settings.AUTH_ADMIN_ROLE], auth_mode="dev")


def _roles_from(value) -> list[str]:
    if not value:
        return []
    if isinstance(value, str):
        return [r.strip() for r in value.replace(",", " ").split() if r.strip()]
    return list(value)


def _from_jwt(token: str) -> CurrentUser:
    import jwt  # lazy: PyJWT only needed in jwt mode

    audience = settings.AUTH_JWT_AUDIENCE or None
    options = {"verify_aud": bool(audience)}
    if settings.AUTH_JWT_JWKS_URL:
        signing_key = jwt.PyJWKClient(settings.AUTH_JWT_JWKS_URL).get_signing_key_from_jwt(token).key
        claims = jwt.decode(token, signing_key, algorithms=["RS256", "ES256"],
                            audience=audience, options=options)
    else:
        claims = jwt.decode(token, settings.AUTH_JWT_SECRET, algorithms=[settings.AUTH_JWT_ALGORITHM],
                            audience=audience, options=options)
    oid = claims.get("sub") or claims.get("oid") or claims.get("email") or "unknown"
    name = claims.get("name") or claims.get("preferred_username") or oid
    roles = _roles_from(claims.get(settings.AUTH_ROLES_CLAIM) or claims.get("roles"))
    return CurrentUser(oid=str(oid), name=str(name), email=claims.get("email"),
                       roles=roles, auth_mode="jwt")


def _from_header(request: Request) -> CurrentUser:
    oid = request.headers.get(settings.AUTH_HEADER_NAME)
    if not oid:
        raise ValueError("missing identity header")
    name = request.headers.get(settings.AUTH_HEADER_DISPLAY_NAME) or oid
    roles = _roles_from(request.headers.get(settings.AUTH_HEADER_ROLES))
    return CurrentUser(oid=oid, name=name, roles=roles, auth_mode="header")


async def get_current_user(request: Request) -> CurrentUser:
    mode = (settings.AUTH_MODE or "dev").lower()
    try:
        if mode == "jwt":
            authz = request.headers.get("authorization", "")
            if authz.lower().startswith("bearer "):
                return _from_jwt(authz[7:].strip())
        elif mode == "header":
            return _from_header(request)
    except HTTPException:
        raise
    except Exception:
        # A presented-but-invalid credential is rejected when auth is required.
        if settings.AUTH_REQUIRED:
            raise HTTPException(status_code=401, detail="Ongeldige authenticatie.")
    # No (valid) identity provided.
    if mode != "dev" and settings.AUTH_REQUIRED:
        raise HTTPException(status_code=401, detail="Authenticatie vereist.")
    return _dev_user()


def require_role(role: str):
    """Dependency factory: require `role` (else 403). Use for admin-only routes."""
    async def _checker(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if role not in user.roles:
            raise HTTPException(status_code=403, detail=f"Rol '{role}' vereist voor deze actie.")
        return user
    return _checker


def require_session_access(session: Session | None, user: CurrentUser) -> Session:
    """Return session if it exists, belongs to the user, and is not deleted; else 404."""
    if session is None or session.user_id != user.oid or session.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session
