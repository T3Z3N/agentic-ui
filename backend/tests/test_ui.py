from travel_agent import ui
from travel_agent.catalog import spec_issues
from travel_agent.llm import FakePlanner
from travel_agent.models import Activity, DayPlan, TripPlan


def types(spec):
    return [e["type"] for e in spec["elements"].values()]


def test_preferences_form_binds_state_and_submits(req):
    spec = ui.preferences_form(req)
    assert spec_issues(spec) == []
    assert spec["root"] == "prefs-form"
    assert spec["state"]["prefs"]["destination"] == "Porto"
    assert spec["state"]["prefs"]["days"] == 2
    assert spec["elements"]["budget"]["props"]["value"] == {"$bindState": "/prefs/budget"}
    assert spec["elements"]["submit"]["on"] == {"press": {"action": "submitPreferences"}}


def test_itinerary_has_core_sections(prefs):
    plan = FakePlanner().plan(prefs)
    spec = ui.itinerary(prefs, plan)
    assert spec_issues(spec) == []
    assert types(spec).count("DayCard") == 2
    assert {"BarChart", "Table", "Stat", "Button"} <= set(types(spec))
    assert spec["elements"]["replan"]["on"]["press"]["action"] == "replan"


def test_optional_sections_follow_the_model(prefs):
    plan = FakePlanner().plan(prefs).model_copy(update={"tips": [], "packing_list": []})
    assert "BulletList" not in types(ui.itinerary(prefs, plan))
    plan = plan.model_copy(update={"tips": ["a"], "packing_list": ["b"]})
    assert types(ui.itinerary(prefs, plan)).count("BulletList") == 2


def test_over_budget_is_flagged(prefs):
    plan = TripPlan(summary="s", days=[DayPlan(day=1, title="t", activities=[
        Activity(time="9", name="Yacht", category="activity", cost=5000)])])
    spec = ui.itinerary(prefs, plan)
    labels = [e["props"]["label"] for e in spec["elements"].values() if e["type"] == "Stat"]
    assert "Over budget" in labels


def test_budget_table_total_row(prefs):
    plan = FakePlanner().plan(prefs)
    table = next(e for e in ui.itinerary(prefs, plan)["elements"].values() if e["type"] == "Table")
    assert table["props"]["rows"][-1][0] == "Total"
    assert table["props"]["rows"][-1][2] == f"€{plan.total_cost():,.0f}"


def test_preferences_form_uses_defaults(req, prefs):
    spec = ui.preferences_form(req, defaults=prefs)
    assert spec["state"]["prefs"] == {**prefs.model_dump(), "destination": "Porto", "days": 2}
