"""Letters API — generate standard HR letters as PDFs.

HR generates confirmation / experience / salary / address letters for an
employee, populated from the directory + salary structure. Tenant-scoped.
"""

from datetime import date
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.identity.principal import ROLE_HR_ADMIN, Principal, require_roles
from app.contexts.letters.service import (
    LETTER_KEYS,
    LETTER_TYPES,
    issued_on,
    letter_body,
)
from app.core.audit import record_audit
from app.core.db import get_session

router = APIRouter(prefix="/letters", tags=["letters"])
HR = require_roles(ROLE_HR_ADMIN)


class LetterTypeOut(BaseModel):
    key: str
    label: str
    needs_ctc: bool


@router.get("/types", response_model=list[LetterTypeOut])
async def list_types(
    principal: Annotated[Principal, HR],
) -> list[LetterTypeOut]:
    return [
        LetterTypeOut(key=lt.key, label=lt.label, needs_ctc=lt.needs_ctc)
        for lt in LETTER_TYPES
    ]


@router.get("/{letter_type}/{employee_id}")
async def generate_letter(
    letter_type: str,
    employee_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> Response:
    from fpdf import FPDF

    if letter_type not in LETTER_KEYS:
        raise HTTPException(404, "Unknown letter type")
    emp = (
        await session.execute(
            text("""select trim(concat(first_name,' ',coalesce(last_name,''))) as name,
                       employee_code, designation_c as designation,
                       department_c as department, date_of_joining
                    from ihrms.v_employee where employee_id = :e"""),
            {"e": employee_id},
        )
    ).mappings().first()
    if emp is None:
        raise HTTPException(404, "Employee not found")
    ctc = (
        await session.execute(
            text("""select ctc_annual from ihrms.salary_structure
                    where employee_id = :e and is_active"""),
            {"e": employee_id},
        )
    ).scalar()

    today = date.today()
    ctx = {
        "name": emp["name"], "designation": emp["designation"],
        "department": emp["department"], "employee_code": emp["employee_code"],
        "date_of_joining": emp["date_of_joining"],
        "ctc_annual": Decimal(str(ctc)) if ctc is not None else None,
        "today": today,
    }
    title, paragraphs = letter_body(letter_type, ctx)

    pdf = FPDF(format="A4")
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 15)
    pdf.cell(0, 10, "Atvantiq People", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 6, issued_on(today), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 10, title, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 11)
    for para in paragraphs:
        pdf.multi_cell(0, 7, para)
        pdf.ln(3)

    await record_audit(
        session, principal, "letter.generate", "employee", str(employee_id),
        summary=f"Generated {letter_type} letter",
    )
    await session.commit()
    return Response(
        content=bytes(pdf.output()), media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{letter_type}_{employee_id}.pdf"'},
    )
