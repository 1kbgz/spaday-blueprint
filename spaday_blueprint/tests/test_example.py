import asyncio

import httpx
import pytest

from spaday_blueprint import example


async def request(method: str, path: str, **kwargs):
    transport = httpx.ASGITransport(app=example.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://example") as client:
        return await client.request(method, path, **kwargs)


def run_ticks(monkeypatch, ticks: int):
    """Run the release stream for ``ticks`` iterations."""
    sleeps = 0

    class Done(Exception):
        pass

    async def sleep(_delay):
        nonlocal sleeps
        sleeps += 1
        if sleeps > ticks:
            raise Done

    monkeypatch.setattr(example.asyncio, "sleep", sleep)
    with pytest.raises(Done):
        asyncio.run(example.stream_release())


def test_example_serves_the_console():
    response = asyncio.run(request("GET", "/tree.json"))
    assert response.status_code == 200
    for tag in ("bp-card", "bp-tabs", "bp-select", "bp-range", "bp-dialog", "bp-toast", "spa-each"):
        assert tag in response.text


def test_deploying_rolls_out_until_live(monkeypatch):
    response = asyncio.run(
        request(
            "POST",
            "/api/deployments",
            json={
                "service": "search",
                "version": "v5.3.0",
                "replicas": "4",
                "scheduled": "2026-09-15",
                "traffic": "25",
                "strategy": "blue-green",
                "canary": True,
            },
        )
    )
    assert response.status_code == 200
    rollout = example.feed.rollouts[0]
    assert response.json()["message"] == f"{rollout['id']}: Search v5.3.0 on 4 replicas, blue-green, canary at 25% of traffic, from 2026-09-15."
    assert (rollout["progress"], rollout["status"]) == (0, "Rolling out")
    run_ticks(monkeypatch, 5)
    landed = next(row for row in example.feed.rollouts if row["id"] == rollout["id"])
    assert (landed["progress"], landed["status"]) == (100, "Live")
    assert next(row for row in example.feed.services if row["id"] == "search")["version"] == "v5.3.0"
    assert asyncio.run(request("POST", "/api/deployments", json={"service": "nope", "version": "v1"})).status_code == 422


def test_restart_and_acknowledge():
    response = asyncio.run(request("POST", "/api/services/worker/restart"))
    assert response.json() == {"message": "Restarted Job workers"}
    worker = next(row for row in example.feed.services if row["id"] == "worker")
    assert (worker["cpu"], worker["status"]) == (20, "success")
    assert asyncio.run(request("POST", "/api/services/nope/restart")).status_code == 404
    open_incident = next(row for row in example.feed.incidents if not row["acknowledged"])
    before = example.feed.open_incidents
    assert asyncio.run(request("POST", f"/api/incidents/{open_incident['id']}/acknowledge")).json() == {
        "message": f"Acknowledged {open_incident['id']}"
    }
    assert example.feed.open_incidents == before - 1
    assert asyncio.run(request("POST", "/api/incidents/INC-0/acknowledge")).status_code == 404


def test_a_saturated_service_raises_an_incident(monkeypatch):
    example.feed.services = example.replace(example.feed.services, "billing", **example.service("billing", 95))
    run_ticks(monkeypatch, 1)
    assert example.feed.incidents[0]["text"].startswith("Billing is saturated")
    assert example.feed.incidents[0]["status"] == "danger"
