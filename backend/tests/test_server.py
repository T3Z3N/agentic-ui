"""End-to-end over the real AG-UI HTTP+SSE protocol, with the fake planner."""

import json

import pytest
from fastapi.testclient import TestClient

from travel_agent.llm import FakePlanner
from travel_agent.server import create_app


@pytest.fixture
def client():
    return TestClient(create_app(FakePlanner()))


def run(client, thread, run_id, text, state=None):
    body = {"threadId": thread, "runId": run_id, "state": state or {},
            "messages": [{"id": f"m-{run_id}", "role": "user", "content": text}],
            "tools": [], "context": [], "forwardedProps": {}}
    r = client.post("/agent", json=body, headers={"accept": "text/event-stream"})
    assert r.status_code == 200
    return [json.loads(line[5:]) for line in r.text.splitlines() if line.startswith("data:")]


def final_state(events):
    return [e for e in events if e["type"] == "STATE_SNAPSHOT"][-1]["snapshot"]


def test_health(client):
    assert client.get("/agent/health").json()["agent"]["name"] == "travel_planner"


def test_run_lifecycle_and_no_raw_events(client):
    events = run(client, "t1", "r1", "Plan 2 days in Porto")
    kinds = [e["type"] for e in events]
    assert kinds[0] == "RUN_STARTED" and kinds[-1] == "RUN_FINISHED"
    assert "RAW" not in kinds
    assert "MESSAGES_SNAPSHOT" in kinds


def test_two_turn_human_in_the_loop(client):
    spec = final_state(run(client, "t2", "r1", "Plan 2 days in Porto"))["ui_spec"]
    assert spec["root"] == "prefs-form"

    prefs = {**spec["state"]["prefs"], "budget": 800}  # what the form would submit
    state = final_state(run(client, "t2", "r2", "Here are my preferences", {"preferences": prefs}))
    assert state["ui_spec"]["root"] == "itinerary"
    days = [e for e in state["ui_spec"]["elements"].values() if e["type"] == "DayCard"]
    assert len(days) == 2


def test_cors_allows_vite_dev_origin(client):
    r = client.options("/agent", headers={"Origin": "http://localhost:5173",
                                          "Access-Control-Request-Method": "POST"})
    assert r.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_malformed_request_is_rejected(client):
    assert client.post("/agent", json={"nope": True}).status_code == 422
