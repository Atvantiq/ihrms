"""Supabase Auth (shared with ONAQT) — JWT validation.

Login happens against the shared Supabase project; iHRMS validates the JWT
and resolves the employee + roles via ihrms.user_account
(auth_user_id uuid <-> employee_id bigint bridge).
"""

from typing import Annotated, Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.core.config import get_settings

bearer = HTTPBearer(auto_error=False)


def decode_supabase_jwt(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except JWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token") from exc
    return payload


def current_auth_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> dict[str, Any]:
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")
    return decode_supabase_jwt(credentials.credentials)


def require_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> dict[str, Any]:
    """Auth gate for protected endpoints.

    DEV ONLY: when settings.auth_disabled is true (local .env), requests pass
    without a token so screens can be built before Supabase keys are wired.
    Never enable outside the dev environment.
    """
    settings = get_settings()
    if settings.auth_disabled and settings.environment == "dev":
        return {"sub": "dev-bypass", "role": "authenticated"}
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")
    return decode_supabase_jwt(credentials.credentials)
