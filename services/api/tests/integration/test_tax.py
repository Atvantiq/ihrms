"""Integration tests for tax declarations + TDS wiring on approval."""

from decimal import Decimal

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

EMP_ID = 100000000002
FY = "2026-27"


async def test_sections_listed(client: AsyncClient, emp_headers: dict[str, str]) -> None:
    secs = (await client.get("/api/v1/tax/sections", headers=emp_headers)).json()
    keys = {s["key"] for s in secs}
    assert {"80C", "80D", "80CCD1B"} <= keys


async def test_empty_declaration_defaults_to_draft(
    client: AsyncClient, emp_headers: dict[str, str]
) -> None:
    decl = (await client.get(f"/api/v1/tax/declaration?fy={FY}", headers=emp_headers)).json()
    assert decl["status"] == "draft"
    assert decl["items"] == []
    assert Decimal(decl["eligible_deduction"]) == 0


async def test_save_caps_eligible_deduction(
    client: AsyncClient, emp_headers: dict[str, str]
) -> None:
    saved = await client.put(
        "/api/v1/tax/declaration", headers=emp_headers,
        json={"fy": FY, "regime": "old",
              "items": [{"section": "80C", "amount": "200000"},
                        {"section": "80D", "amount": "20000"}]},
    )
    assert saved.status_code == 200, saved.text
    body = saved.json()
    # 80C capped at 150k + 80D 20k = 170k eligible (declared 220k)
    assert Decimal(body["declared_total"]) == 220000
    assert Decimal(body["eligible_deduction"]) == 170000


async def test_unknown_section_rejected(
    client: AsyncClient, emp_headers: dict[str, str]
) -> None:
    r = await client.put(
        "/api/v1/tax/declaration", headers=emp_headers,
        json={"fy": FY, "items": [{"section": "bogus", "amount": "1000"}]},
    )
    assert r.status_code == 404


async def test_submit_approve_wires_tds(
    client: AsyncClient, hr_headers: dict[str, str], emp_headers: dict[str, str]
) -> None:
    # employee needs an active structure for the deduction to land on
    await client.put(
        f"/api/v1/payroll/structures/{EMP_ID}", headers=hr_headers,
        json={"ctc_annual": 2000000, "effective_from": "2026-04-01", "tax_regime": "new"},
    )
    # declare 80C 150k (old regime) and submit
    await client.put(
        "/api/v1/tax/declaration", headers=emp_headers,
        json={"fy": FY, "regime": "old", "items": [{"section": "80C", "amount": "150000"}]},
    )
    submitted = await client.post(f"/api/v1/tax/declaration/submit?fy={FY}", headers=emp_headers)
    assert submitted.status_code == 200
    decl_id = submitted.json()["id"]
    # cannot edit once submitted
    locked = await client.put(
        "/api/v1/tax/declaration", headers=emp_headers,
        json={"fy": FY, "items": [{"section": "80C", "amount": "1"}]},
    )
    assert locked.status_code == 409

    # HR approves -> structure picks up old regime + 150k deduction
    appr = await client.post(f"/api/v1/tax/declaration/{decl_id}/approve", headers=hr_headers)
    assert appr.status_code == 200
    assert appr.json()["status"] == "approved"

    struct = (
        await client.get(f"/api/v1/payroll/structures/{EMP_ID}", headers=hr_headers)
    ).json()
    assert struct["tax_regime"] == "old"
    assert Decimal(struct["chapter_via_deductions"]) == 150000


async def test_employee_cannot_approve(
    client: AsyncClient, emp_headers: dict[str, str]
) -> None:
    r = await client.post("/api/v1/tax/declaration/some-id/approve", headers=emp_headers)
    assert r.status_code == 403
