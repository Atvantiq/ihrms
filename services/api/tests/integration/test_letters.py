"""Integration tests for letter generation (PDF downloads)."""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

EMP_ID = 100000000002


async def test_types_listed(client: AsyncClient, hr_headers: dict[str, str]) -> None:
    types = (await client.get("/api/v1/letters/types", headers=hr_headers)).json()
    keys = {t["key"] for t in types}
    assert {"confirmation", "experience", "salary_certificate"} <= keys


async def test_non_hr_forbidden(client: AsyncClient, emp_headers: dict[str, str]) -> None:
    r = await client.get(f"/api/v1/letters/experience/{EMP_ID}", headers=emp_headers)
    assert r.status_code == 403


async def test_generate_experience_pdf(
    client: AsyncClient, hr_headers: dict[str, str]
) -> None:
    r = await client.get(f"/api/v1/letters/experience/{EMP_ID}", headers=hr_headers)
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content[:4] == b"%PDF"


async def test_unknown_type_404(client: AsyncClient, hr_headers: dict[str, str]) -> None:
    r = await client.get(f"/api/v1/letters/promotion/{EMP_ID}", headers=hr_headers)
    assert r.status_code == 404
