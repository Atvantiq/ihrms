"""Integration tests for the custom report builder endpoints."""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_datasets_listed(client: AsyncClient, hr_headers: dict[str, str]) -> None:
    ds = (await client.get("/api/v1/reports/datasets", headers=hr_headers)).json()
    keys = {d["key"] for d in ds}
    assert {"employees", "leave_requests", "payslips_latest"} <= keys
    emp = next(d for d in ds if d["key"] == "employees")
    assert any(c["key"] == "name" for c in emp["columns"])
    assert any(f["key"] == "department" for f in emp["filters"])


async def test_build_runs_against_seeded_employees(
    client: AsyncClient, hr_headers: dict[str, str]
) -> None:
    r = await client.post(
        "/api/v1/reports/build", headers=hr_headers,
        json={"dataset": "employees", "columns": ["employee_code", "name"],
              "filters": [], "limit": 10},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["columns"] == ["employee_code", "name"]
    assert len(body["rows"]) >= 1
    assert "name" in body["rows"][0]


async def test_build_rejects_unknown_column(
    client: AsyncClient, hr_headers: dict[str, str]
) -> None:
    r = await client.post(
        "/api/v1/reports/build", headers=hr_headers,
        json={"dataset": "employees", "columns": ["name; drop table employees"]},
    )
    assert r.status_code == 422


async def test_build_rejects_unknown_dataset(
    client: AsyncClient, hr_headers: dict[str, str]
) -> None:
    r = await client.post(
        "/api/v1/reports/build", headers=hr_headers, json={"dataset": "pg_catalog"}
    )
    assert r.status_code == 422


async def test_build_csv_and_non_hr_blocked(
    client: AsyncClient, hr_headers: dict[str, str], emp_headers: dict[str, str]
) -> None:
    csv = await client.post(
        "/api/v1/reports/build/csv", headers=hr_headers,
        json={"dataset": "employees", "columns": ["employee_code", "name"]},
    )
    assert csv.status_code == 200
    assert "employee_code" in csv.text

    blocked = await client.post(
        "/api/v1/reports/build", headers=emp_headers, json={"dataset": "employees"}
    )
    assert blocked.status_code == 403
