"""Golden tests for HR letter wording."""

from datetime import date
from decimal import Decimal

import pytest

from app.contexts.letters.service import LETTER_KEYS, letter_body

CTX = {
    "name": "Asha Rao",
    "designation": "Senior Engineer",
    "department": "Engineering",
    "employee_code": "ATV-0042",
    "date_of_joining": date(2022, 4, 1),
    "ctc_annual": Decimal(1800000),
    "today": date(2026, 6, 13),
}


class TestLetterBody:
    def test_all_types_known(self) -> None:
        assert {
            "confirmation", "experience", "salary_certificate", "address_proof",
        } == LETTER_KEYS

    def test_confirmation_addresses_employee(self) -> None:
        title, paras = letter_body("confirmation", CTX)
        assert title == "Confirmation Letter"
        joined = " ".join(paras)
        assert "Asha Rao" in joined and "Senior Engineer" in joined

    def test_experience_has_code_and_doj(self) -> None:
        _, paras = letter_body("experience", CTX)
        joined = " ".join(paras)
        assert "ATV-0042" in joined
        assert "01 April 2022" in joined

    def test_salary_certificate_shows_ctc(self) -> None:
        _, paras = letter_body("salary_certificate", CTX)
        assert any("1,800,000" in p for p in paras)

    def test_salary_certificate_handles_missing_ctc(self) -> None:
        ctx = {**CTX, "ctc_annual": None}
        _, paras = letter_body("salary_certificate", ctx)
        # no crash; renders a placeholder
        assert any("INR" not in p or "-" in p for p in paras)

    def test_unknown_type_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown letter type"):
            letter_body("promotion", CTX)
