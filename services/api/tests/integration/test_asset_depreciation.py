"""Integration test for the asset depreciation report."""

from decimal import Decimal

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_non_hr_forbidden(client: AsyncClient, emp_headers: dict[str, str]) -> None:
    assert (await client.get("/api/v1/assets/depreciation", headers=emp_headers)).status_code == 403


async def test_depreciation_totals(client: AsyncClient, hr_headers: dict[str, str]) -> None:
    # a laptop bought a while back depreciates below cost but above zero
    await client.post(
        "/api/v1/assets", headers=hr_headers,
        json={"asset_tag": "DEP-1", "category": "laptop", "name": "Old ThinkPad",
              "purchase_date": "2025-01-01", "purchase_cost": "120000"},
    )
    rep = (await client.get("/api/v1/assets/depreciation", headers=hr_headers)).json()
    line = next(x for x in rep["lines"] if x["asset_tag"] == "DEP-1")
    cost = Decimal(line["purchase_cost"])
    bv = Decimal(line["book_value"])
    assert 0 < bv < cost
    assert Decimal(line["depreciated"]) == cost - bv
    # totals are internally consistent
    assert Decimal(rep["total_depreciated"]) == (
        Decimal(rep["total_cost"]) - Decimal(rep["total_book_value"])
    )
