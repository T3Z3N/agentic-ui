"""Regression: internal structured-output LLM calls must not leak raw JSON tokens
into the chat. Found against real llama3.1:8b: the AG-UI bridge streamed
'{ "destination": "Barcelona", ' as an assistant message while the run was going."""

import json

from fastapi.testclient import TestClient
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from travel_agent.llm import INTERNAL_LLM_CONFIG, FakePlanner
from travel_agent.models import TripRequest
from travel_agent.server import create_app


class StreamingPlanner(FakePlanner):
    """Calls a real (fake) chat model, so the bridge sees on_chat_model_stream events."""

    def parse_request(self, text: str) -> TripRequest:
        raw = '{"destination": "Barcelona", "days": 2}'
        model = GenericFakeChatModel(messages=iter([AIMessage(content=raw)]))
        out = model.with_config(INTERNAL_LLM_CONFIG).invoke(text)
        return TripRequest.model_validate_json(out.content)


def test_internal_llm_tokens_are_not_streamed_to_chat():
    client = TestClient(create_app(StreamingPlanner()))
    body = {"threadId": "leak", "runId": "r1", "state": {},
            "messages": [{"id": "m1", "role": "user", "content": "2 days in Barcelona"}],
            "tools": [], "context": [], "forwardedProps": {}}
    r = client.post("/agent", json=body, headers={"accept": "text/event-stream"})
    events = [json.loads(line[5:]) for line in r.text.splitlines() if line.startswith("data:")]
    streamed = "".join(e.get("delta", "") for e in events if e["type"] == "TEXT_MESSAGE_CONTENT")
    assert "destination" not in streamed
    snapshot = [e for e in events if e["type"] == "STATE_SNAPSHOT"][-1]["snapshot"]
    assert snapshot["ui_spec"]["state"]["prefs"]["destination"] == "Barcelona"


def test_ollama_planner_marks_its_calls_internal():
    from travel_agent.llm import OllamaPlanner

    p = OllamaPlanner()
    for runnable in (p._request, p._plan):
        assert runnable.config["metadata"]["emit-messages"] is False
