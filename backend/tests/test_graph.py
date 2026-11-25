from langchain_core.messages import AIMessage, HumanMessage

from travel_agent.catalog import spec_issues
from travel_agent.graph import build_graph
from travel_agent.llm import FakePlanner


def run(graph, thread, **state):
    return graph.invoke(state, {"configurable": {"thread_id": thread}})


def test_first_turn_asks_for_preferences():
    out = run(build_graph(FakePlanner()), "t", messages=[HumanMessage("Plan 4 days in Rome")])
    assert out["ui_spec"]["root"] == "prefs-form"
    assert out["ui_spec"]["state"]["prefs"]["days"] == 4
    assert isinstance(out["messages"][-1], AIMessage)


def test_submitted_preferences_produce_itinerary(prefs):
    g = build_graph(FakePlanner())
    run(g, "t", messages=[HumanMessage("Plan 2 days in Porto")])
    out = run(g, "t", messages=[HumanMessage("Here are my preferences")],
              preferences=prefs.model_dump())
    assert out["ui_spec"]["root"] == "itinerary"
    assert spec_issues(out["ui_spec"]) == []
    assert "Estimated total" in out["messages"][-1].content
    assert len(out["messages"]) == 4  # history is kept by the checkpointer


def test_invalid_preferences_render_error_and_reset():
    out = run(build_graph(FakePlanner()), "t", messages=[HumanMessage("go")],
              preferences={"destination": "", "days": 99, "budget": 1})
    assert out["ui_spec"]["elements"]["error"]["props"]["title"] == "Invalid preferences"
    assert out["preferences"] is None
    assert spec_issues(out["ui_spec"]) == []


class Broken(FakePlanner):
    def parse_request(self, text):
        raise ConnectionError("ollama not running")

    def plan(self, prefs):
        raise TimeoutError("model timed out")


def test_model_failure_degrades_gracefully(prefs):
    g = build_graph(Broken())
    out = run(g, "a", messages=[HumanMessage("hi")])
    assert "ollama not running" in out["ui_spec"]["elements"]["msg"]["props"]["text"]
    out = run(g, "b", messages=[HumanMessage("hi")], preferences=prefs.model_dump())
    assert out["ui_spec"]["elements"]["error"]["props"]["title"] == "Planning failed"


def test_multimodal_content_is_read_as_text():
    out = run(build_graph(FakePlanner()), "t",
              messages=[HumanMessage(content=[{"type": "text", "text": "6 days in Oslo"}])])
    assert out["ui_spec"]["state"]["prefs"] == {
        "destination": "Oslo", "days": 6, "budget": 1000, "style": "balanced", "interests": ""}


def test_new_chat_after_itinerary_starts_a_new_trip(prefs):
    """Submitted preferences are consumed, so a fresh request isn't silently re-planned."""
    g = build_graph(FakePlanner())
    run(g, "t", messages=[HumanMessage("x")], preferences=prefs.model_dump())
    out = run(g, "t", messages=[HumanMessage("Now plan 4 days in Rome")])
    assert out["ui_spec"]["root"] == "prefs-form"
    assert out["ui_spec"]["state"]["prefs"]["destination"] == "Rome"
    assert out["preferences"] is None


def test_change_preferences_prefills_last_trip_without_llm(prefs):
    class NoLLM(FakePlanner):
        def parse_request(self, text):
            raise AssertionError("edit_preferences must not call the model")

    g = build_graph(NoLLM())
    run(g, "t", messages=[HumanMessage("x")], preferences=prefs.model_dump())
    out = run(g, "t", messages=[HumanMessage("I'd like to change my preferences.")],
              edit_preferences=True, preferences=None)
    assert out["ui_spec"]["state"]["prefs"] == prefs.model_dump()
    assert out["edit_preferences"] is False
    assert spec_issues(out["ui_spec"]) == []


def test_change_preferences_without_history_falls_back_to_asking():
    out = run(build_graph(FakePlanner()), "t",
              messages=[HumanMessage("3 days in Oslo")], edit_preferences=True)
    assert out["ui_spec"]["state"]["prefs"]["destination"] == "Oslo"
    assert out["edit_preferences"] is False
