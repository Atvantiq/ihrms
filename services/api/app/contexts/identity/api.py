from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.contexts.identity.principal import Principal, get_current_principal

router = APIRouter(prefix="/me", tags=["me"])


class MeOut(BaseModel):
    employee_id: int
    email: str
    roles: list[str]
    persona: str
    is_hr: bool


@router.get("", response_model=MeOut)
async def me(
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> MeOut:
    return MeOut(
        employee_id=principal.employee_id,
        email=principal.email,
        roles=principal.roles,
        persona=principal.persona,
        is_hr=principal.is_hr,
    )
