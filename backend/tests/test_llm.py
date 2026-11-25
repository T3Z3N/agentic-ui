import pytest
from langchain_core.runnables import RunnableLambda

from travel_agent import llm
from travel_agent.llm import FakePlanner, OllamaPlanner, get_planner
from travel_agent.models import Activity, DayPlan, TripPlan


@pytest.mark.parametrize("text, dest, days", [
    ("Plan 3 days in Lisbon", "Lisbon", 3),
    ("I want to visit Kyoto for 5 days", "Kyoto", 5),
    ("A 2-day trip to New York!", "New York", 2),
    ("surprise me", "Lisbon", 3),            # defaults
    ("40 days in Rome", "Rome", 14),         # clamped to max
])
def test_fake_parse_request(text, dest, days):
    r = FakePlanner().parse_request(text)
    assert (r.destination, r.days) == (dest, days)


def test_fake_plan_respects_days_and_budget(prefs):
    plan = FakePlanner().plan(prefs)
    assert [d.day for d in plan.days] == [1, 2]
    assert plan.total_cost() <= prefs.budget


def test_get_planner_selects_provider(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    assert isinstance(get_planner(), FakePlanner)
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    assert isinstance(get_planner(), OllamaPlanner)  # constructing makes no network call
    monkeypatch.setenv("LLM_PROVIDER", "gpt-9000")
    with pytest.raises(ValueError, match="Unknown LLM_PROVIDER"):
        get_planner()


def test_ollama_planner_renumbers_and_trims_days(prefs):
    """Small models miscount days; the planner must trust the user's day count."""
    sloppy = TripPlan(summary="s", days=[
        DayPlan(day=d, title=f"d{d}", activities=[Activity(time="9", name="x", category="food", cost=1)])
        for d in (4, 7, 9)
    ])
    p = OllamaPlanner()
    p._plan = RunnableLambda(lambda _: sloppy)
    plan = p.plan(prefs)  # prefs.days == 2
    assert [(d.day, d.title) for d in plan.days] == [(1, "d4"), (2, "d7")]


def test_ollama_prompt_includes_preferences(prefs):
    msgs = llm.PLAN_PROMPT.invoke(prefs.model_dump()).to_messages()
    text = " ".join(m.content for m in msgs)
    assert "Porto" in text and "600" in text and "wine" in text


# --- normalize_time / tidy_plan: clean-up of real llama3.1:8b quirks ----------
from travel_agent.llm import normalize_time, tidy_plan  # noqa: E402


@pytest.mark.parametrize("raw, expected", [
    ("09:00", "09:00"),
    ("9:00 AM", "09:00"),
    (": 12:00 PM", "12:00"),   # seen verbatim from llama3.1:8b
    ("12:30 am", "00:30"),
    ("7pm", "19:00"),
    ("7 p.m.", "19:00"),
    ("19h30", "19:30"),
    ("14.15", "14:15"),
    ("Evening", "Evening"),    # unparseable -> left as-is
    ("25:00", "25:00"),        # out of range -> left as-is
])
def test_normalize_time(raw, expected):
    assert normalize_time(raw) == expected


def test_tidy_plan_sorts_normalised_times(prefs):
    acts = [Activity(time=t, name=t, category="sight", cost=0) for t in ("2:00 PM", "9:30 AM", "11:00")]
    plan = TripPlan(summary="s", days=[DayPlan(day=5, title="t", activities=acts)])
    tidy = tidy_plan(plan, prefs)
    assert tidy.days[0].day == 1
    assert [a.time for a in tidy.days[0].activities] == ["09:30", "11:00", "14:00"]


def test_plan_prompt_demands_24h_times_and_accommodation(prefs):
    text = " ".join(m.content for m in llm.PLAN_PROMPT.invoke(prefs.model_dump()).to_messages())
    assert "24-hour" in text and "'stay'" in text and "70-100%" in text
