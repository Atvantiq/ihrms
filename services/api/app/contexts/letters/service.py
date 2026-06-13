"""HR letter templates — build the title + body text for each letter type.

Pure: takes an employee context dict and returns (title, paragraphs). The PDF
layer wraps this. Keeping it pure makes the wording golden-testable.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class LetterType:
    key: str
    label: str
    needs_ctc: bool


LETTER_TYPES: list[LetterType] = [
    LetterType("confirmation", "Confirmation letter", False),
    LetterType("experience", "Experience certificate", False),
    LetterType("salary_certificate", "Salary certificate", True),
    LetterType("address_proof", "Employment / address proof", False),
]
LETTER_KEYS = frozenset(lt.key for lt in LETTER_TYPES)


def _inr(v: Decimal) -> str:
    return "INR " + f"{int(v):,}"


def letter_body(letter_type: str, ctx: dict[str, object]) -> tuple[str, list[str]]:
    """Return (title, paragraphs). `ctx` carries: name, designation, department,
    employee_code, date_of_joining (date), ctc_annual (Decimal|None), today (date)."""
    name = str(ctx.get("name") or "")
    desig = str(ctx.get("designation") or "")
    dept = str(ctx.get("department") or "")
    code = str(ctx.get("employee_code") or "")
    doj = ctx.get("date_of_joining")
    doj_s = f"{doj:%d %B %Y}" if isinstance(doj, date) else "-"

    if letter_type == "confirmation":
        return "Confirmation Letter", [
            f"Dear {name},",
            f"We are pleased to confirm your employment with Atvantiq as "
            f"{desig} in the {dept} department, following the successful "
            f"completion of your probation period.",
            "Your continued employment is governed by the terms of your "
            "appointment. We look forward to your contributions.",
            "Warm regards,\nHuman Resources, Atvantiq People",
        ]
    if letter_type == "experience":
        return "Experience Certificate", [
            "To Whomsoever It May Concern",
            f"This is to certify that {name} (Employee ID {code}) has been "
            f"employed with Atvantiq as {desig} in the {dept} department "
            f"since {doj_s}.",
            "During their tenure they have been found to be sincere, "
            "diligent and professional in conduct.",
            "Issued on behalf of Human Resources, Atvantiq People.",
        ]
    if letter_type == "salary_certificate":
        ctc = ctx.get("ctc_annual")
        ctc_s = _inr(ctc) if isinstance(ctc, Decimal) else "-"
        return "Salary Certificate", [
            "To Whomsoever It May Concern",
            f"This is to certify that {name} (Employee ID {code}) is employed "
            f"with Atvantiq as {desig}, with an annual cost-to-company of "
            f"{ctc_s}.",
            "This certificate is issued on request for the employee's records.",
            "Human Resources, Atvantiq People.",
        ]
    if letter_type == "address_proof":
        return "Employment / Address Proof", [
            "To Whomsoever It May Concern",
            f"This is to certify that {name} (Employee ID {code}) is a "
            f"current employee of Atvantiq, working as {desig} in the {dept} "
            f"department since {doj_s}.",
            "This letter is issued for the purpose of address and employment "
            "verification.",
            "Human Resources, Atvantiq People.",
        ]
    raise ValueError(f"Unknown letter type: {letter_type}")


def issued_on(today: date) -> str:
    return f"Issued on {today:%d %B %Y}"
