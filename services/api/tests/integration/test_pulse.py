"""Integration tests for the Pulse decision inbox."""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_inbox_requires_auth(client: AsyncClient) -> None:
    assert (await client.get("/api/v1/pulse/inbox")).status_code == 401


async def test_pending_leave_surfaces_as_decision(
    client: AsyncClient, hr_headers: dict[str, str], emp_headers: dict[str, str]
) -> None:
    # baseline count (the shared DB may already hold pending requests)
    def leave_count(inbox: list[dict[str, object]]) -> int:
        card = next((d for d in inbox if d["kind"] == "leave_approvals"), None)
        return int(card["count"]) if card else 0  # type: ignore[arg-type]

    before = leave_count((await client.get("/api/v1/pulse/inbox", headers=hr_headers)).json())

    # an employee applies for leave -> one more pending request exists
    types = (await client.get("/api/v1/leave/types", headers=emp_headers)).json()
    cl = next(t for t in types if t["code"] == "CL")
    apply = await client.post(
        "/api/v1/leave/requests",
        headers=emp_headers,
        json={"leave_type_id": cl["id"], "start_date": "2026-08-03", "end_date": "2026-08-04"},
    )
    assert apply.status_code == 201, apply.text

    # HR's inbox now carries a ranked leave-approvals decision with +1 count
    after = (await client.get("/api/v1/pulse/inbox", headers=hr_headers)).json()
    card = next((d for d in after if d["kind"] == "leave_approvals"), None)
    assert card is not None
    assert card["count"] == before + 1
    assert card["action_href"] == "/tasks"  # approval cards route to the unified inbox
    assert card["severity"] in ("high", "medium", "low")


async def test_inbox_is_ranked_high_first(
    client: AsyncClient, hr_headers: dict[str, str]
) -> None:
    inbox = (await client.get("/api/v1/pulse/inbox", headers=hr_headers)).json()
    weights = {"high": 0, "medium": 1, "low": 2}
    seq = [weights[d["severity"]] for d in inbox]
    assert seq == sorted(seq)  # severity never increases down the list
