"""DEV-ONLY password-free sign-in.

Mints a valid Supabase-signed JWT for the seeded HR admin so the app can be
explored locally without a password. Hard-gated: returns 404 unless
environment == 'dev' AND dev_login_enabled is true. Never enable in prod.
"""

import time
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from jose import jwt
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import get_session

router = APIRouter(prefix="/auth", tags=["auth"])


class DevSession(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict[str, Any]


@router.post("/dev-login", response_model=DevSession)
async def dev_login(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> DevSession:
    settings = get_settings()
    if not (settings.environment == "dev" and settings.dev_login_enabled):
        raise HTTPException(404, "Not found")

    row = (
        await session.execute(
            text("""select u.id::text as uid, u.email
                    from ihrms.user_account ua
                    join auth.users u on u.id = ua.auth_user_id
                    where 'hr_admin' = any(ua.roles) and ua.is_active
                    order by u.email limit 1""")
        )
    ).mappings().first()
    if row is None:
        raise HTTPException(404, "No HR admin account available")

    now = int(time.time())
    exp = now + 3600
    token = jwt.encode(
        {
            "sub": row["uid"],
            "email": row["email"],
            "aud": "authenticated",
            "role": "authenticated",
            "iat": now,
            "exp": exp,
        },
        settings.supabase_jwt_secret,
        algorithm="HS256",
    )
    return DevSession(
        access_token=token,
        refresh_token="dev-no-refresh",
        expires_in=3600,
        user={
            "id": row["uid"],
            "email": row["email"],
            "aud": "authenticated",
            "role": "authenticated",
        },
    )
