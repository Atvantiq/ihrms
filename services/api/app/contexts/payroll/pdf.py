"""Payslip PDF generation (fpdf2 — pure Python, no system deps)."""

from typing import Any

from fpdf import FPDF

MONTHS = [
    "", "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]

LABELS = {
    "basic": "Basic", "hra": "HRA", "special_allowance": "Special Allowance",
    "pf_employee": "Provident Fund", "esi_employee": "ESI", "pt": "Professional Tax",
    "tds": "TDS (Income Tax)",
}


def _inr(v: Any) -> str:
    return f"Rs. {float(v):,.2f}"


def payslip_pdf(
    *, employee_name: str, employee_code: str, payslip: dict[str, Any],
    year: int, month: int,
) -> bytes:
    pdf = FPDF(format="A4")
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Atvantiq People", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 7, f"Payslip - {MONTHS[month]} {year}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Employee: {employee_name}  ({employee_code})",
             new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"LOP days: {payslip['lop_days']}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    def section(title: str, items: dict[str, Any], total_label: str, total: Any) -> None:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, title, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        for k, v in items.items():
            pdf.cell(110, 6, LABELS.get(k, k.replace("_", " ").title()))
            pdf.cell(0, 6, _inr(v), align="R", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(110, 6, total_label)
        pdf.cell(0, 6, _inr(total), align="R", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)

    section("Earnings", payslip["earnings"], "Gross Earnings", payslip["gross"])
    section("Deductions", payslip["deductions"], "Total Deductions",
            payslip["total_deductions"])

    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(110, 9, "Net Pay")
    pdf.cell(0, 9, _inr(payslip["net_pay"]), align="R", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(6)
    pdf.set_font("Helvetica", "I", 8)
    pdf.cell(0, 5, "System-generated payslip. Figures in INR.",
             new_x="LMARGIN", new_y="NEXT")

    return bytes(pdf.output())
