"""Integration test for interview scorecards."""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def _candidate_with_interview(
    client: AsyncClient, hr: dict[str, str], code: str = "REQ-SC-1"
) -> tuple[str, str]:
    req = (await client.post(
        "/api/v1/recruitment/requisitions", headers=hr,
        json={"code": code, "title": "Backend Engineer", "openings": 1},
    )).json()
    cand = (await client.post(
        "/api/v1/recruitment/candidates", headers=hr,
        json={"requisition_id": req["id"], "name": "Riya Sharma",
              "email": "riya@example.com"},
    )).json()
    iv = (await client.post(
        f"/api/v1/recruitment/candidates/{cand['id']}/interviews", headers=hr,
        json={"round": "Tech round 1", "recommendation": "yes"},
    )).json()
    return cand["id"], iv["id"]


async def test_scorecard_aggregates(client: AsyncClient, hr_headers: dict[str, str]) -> None:
    cid, iid = await _candidate_with_interview(client, hr_headers)

    for crit, score in [("Technical", 4), ("Communication", 5), ("Culture", 4)]:
        r = await client.post(
            f"/api/v1/recruitment/interviews/{iid}/scores", headers=hr_headers,
            json={"criterion": crit, "score": score},
        )
        assert r.status_code == 201, r.text

    scores = (await client.get(
        f"/api/v1/recruitment/interviews/{iid}/scores", headers=hr_headers
    )).json()
    assert len(scores) == 3

    card = (await client.get(
        f"/api/v1/recruitment/candidates/{cid}/scorecard", headers=hr_headers
    )).json()
    assert card["total_scores"] == 3
    # overall = (4+5+4)/3 = 4.3
    assert card["overall"] == 4.3
    by = {c["criterion"]: c for c in card["criteria"]}
    assert by["Communication"]["average"] == 5.0


async def test_score_out_of_range_rejected(
    client: AsyncClient, hr_headers: dict[str, str]
) -> None:
    _, iid = await _candidate_with_interview(client, hr_headers, code="REQ-SC-2")
    r = await client.post(
        f"/api/v1/recruitment/interviews/{iid}/scores", headers=hr_headers,
        json={"criterion": "Technical", "score": 9},
    )
    assert r.status_code == 422


async def test_scores_require_hr(client: AsyncClient, emp_headers: dict[str, str]) -> None:
    r = await client.post(
        "/api/v1/recruitment/interviews/00000000-0000-0000-0000-000000000000/scores",
        headers=emp_headers, json={"criterion": "Technical", "score": 4},
    )
    assert r.status_code == 403
