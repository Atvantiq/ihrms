"""Principal resolution: Supabase JWT -> linked employee + iHRMS roles.

Roles (additive): employee < manager < hr_admin < super_admin.
Linking is just-in-time: on first authenticated call, the auth user is
matched to an employee by verified email and a user_account row is created
with the default `employee` role. Unmatched users get 403 — an HR admin
must fix the employee email first.
"""

from typing import Annotated, Any

from fastapi import Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import get_session
from app.core.security import require_user

ROLE_EMPLOYEE = "employee"
ROLE_MANAGER = "manager"
ROLE_HR_ADMIN = "hr_admin"
ROLE_SUPER_ADMIN = "super_admin"


class Principal(BaseModel):
    auth_user_id: str
    email: str
    employee_id: int
    roles: list[str]
    persona: str

    def has_role(self, *roles: str) -> bool:
        return any(r in self.roles for r in roles)

    @property
    def is_hr(self) -> bool:
        return self.has_role(ROLE_HR_ADMIN, ROLE_SUPER_ADMIN)


async def get_current_principal(
    claims: Annotated[dict[str, Any], Depends(require_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Principal:
    settings = get_settings()
    if claims.get("sub") == "dev-bypass" and settings.auth_disabled:
        return Principal(
            auth_user_id="dev-bypass", email="dev@local", employee_id=0,
            roles=[ROLE_EMPLOYEE, ROLE_HR_ADMIN], persona="hr",
        )

    auth_user_id = claims["sub"]
    email = str(claims.get("email", "")).lower()

    row = (
        await session.execute(
            text("""select employee_id, roles, persona, is_active
                    from ihrms.user_account where auth_user_id = :uid"""),
            {"uid": auth_user_id},
        )
    ).mappings().first()

    if row is None:
        # JIT link by verified email
        emp = (
            await session.execute(
                text("""select employee_id from public.employees
                        where lower(email) = :email
                        order by created_at limit 1"""),
                {"email": email},
            )
        ).mappings().first()
        if emp is None:
            raise HTTPException(
                403, "No employee record is linked to this login. Contact HR."
            )
        await session.execute(
            text("""insert into ihrms.user_account (auth_user_id, employee_id)
                    values (:uid, :emp) on conflict (auth_user_id) do nothing"""),
            {"uid": auth_user_id, "emp": emp["employee_id"]},
        )
        await session.commit()
        return Principal(
            auth_user_id=auth_user_id, email=email,
            employee_id=emp["employee_id"], roles=[ROLE_EMPLOYEE], persona="employee",
        )

    if not row["is_active"]:
        raise HTTPException(403, "This account is disabled.")
    return Principal(
        auth_user_id=auth_user_id, email=email, employee_id=row["employee_id"],
        roles=list(row["roles"]), persona=row["persona"],
    )


def require_roles(*roles: str) -> Any:
    async def dep(
        principal: Annotated[Principal, Depends(get_current_principal)],
    ) -> Principal:
        if not principal.has_role(*roles, ROLE_SUPER_ADMIN):
            raise HTTPException(403, "Insufficient permissions.")
        return principal

    return Depends(dep)
