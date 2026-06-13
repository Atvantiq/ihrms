"""Integration tests for bands & grades."""

from decimal import Decimal

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

EMP_ID = 100000000002


async def test_seeded_bands_listed(client: AsyncClient, hr_headers: dict[str, str]) -> None:
    bands = (await client.get("/api/v1/bands", headers=hr_headers)).json()
    codes = {b["code"] for b in bands}
    assert {"L1", "L2", "L3", "L4", "L5"} <= codes


async def test_non_hr_cannot_create(client: AsyncClient, emp_headers: dict[str, str]) -> None:
    r = await client.post(
        "/api/v1/bands", headers=emp_headers,
        json={"code": "X", "name": "X", "level": 1, "min_ctc": "1", "max_ctc": "2"},
    )
    assert r.status_code == 403


async def test_assign_and_band_fit(
    client: AsyncClient, hr_headers: dict[str, str], emp_headers: dict[str, str]
) -> None:
    # give the employee a CTC, then assign an L2 band (800k–1.6M)
    await client.put(
        f"/api/v1/payroll/structures/{EMP_ID}", headers=hr_headers,
        json={"ctc_annual": 1200000, "effective_from": "2026-01-01", "tax_regime": "new"},
    )
    bands = (await client.get("/api/v1/bands", headers=hr_headers)).json()
    l2 = next(b for b in bands if b["code"] == "L2")

    assigned = await client.post(
        "/api/v1/bands/assign", headers=hr_headers,
        json={"employee_id": EMP_ID, "band_id": l2["id"]},
    )
    assert assigned.status_code == 200, assigned.text
    body = assigned.json()
    assert body["band_code"] == "L2"
    assert body["fit"] == "within"  # 1.2M within 800k–1.6M

    # bump CTC beyond the band -> fit flips to "above"
    await client.put(
        f"/api/v1/payroll/structures/{EMP_ID}", headers=hr_headers,
        json={"ctc_annual": 2000000, "effective_from": "2026-02-01", "tax_regime": "new"},
    )
    after = (await client.get(f"/api/v1/bands/employee/{EMP_ID}", headers=emp_headers)).json()
    assert after["fit"] == "above"
    assert Decimal(after["current_ctc"]) == 2000000


async def test_max_below_min_rejected(
    client: AsyncClient, hr_headers: dict[str, str]
) -> None:
    r = await client.post(
        "/api/v1/bands", headers=hr_headers,
        json={"code": "BAD", "name": "Bad", "level": 9, "min_ctc": "900000", "max_ctc": "100000"},
    )
    assert r.status_code == 422
