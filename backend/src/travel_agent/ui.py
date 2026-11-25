"""UI composer: turns domain data into json-render specs (flat element maps).

The LLM decides *what* to say (TripPlan, incl. optional sections); this module
decides *how* it looks, using only catalog components. Keeping the model out of
raw layout makes small local models (Ollama) reliable, and every spec is still
validated against the shared catalog before it leaves the server.
"""

from typing import Any

from .catalog import validate_spec
from .models import TRAVEL_STYLES, Preferences, TripPlan, TripRequest

Spec = dict[str, Any]


class _Builder:
    def __init__(self) -> None:
        self.elements: dict[str, Any] = {}
        self._n = 0

    def add(self, type_: str, props: dict[str, Any], children: list[str] | None = None,
            on: dict[str, Any] | None = None, key: str | None = None) -> str:
        self._n += 1
        key = key or f"{type_.lower()}-{self._n}"
        el: dict[str, Any] = {"type": type_, "props": props, "children": children or []}
        if on:
            el["on"] = on
        self.elements[key] = el
        return key

    def spec(self, root: str, state: dict[str, Any] | None = None) -> Spec:
        spec: Spec = {"root": root, "elements": self.elements}
        if state is not None:
            spec["state"] = state
        return validate_spec(spec)


def _money(v: float) -> str:
    return f"€{v:,.0f}"


def preferences_form(req: TripRequest, defaults: Preferences | None = None) -> Spec:
    """Human-in-the-loop: the agent asks for structured input via a generated form."""
    b = _Builder()
    fields = [
        b.add("TextInput", {"label": "Destination", "value": {"$bindState": "/prefs/destination"},
                            "placeholder": "e.g. Lisbon"}, key="destination"),
        b.add("NumberInput", {"label": "Days", "value": {"$bindState": "/prefs/days"},
                              "min": 1, "max": 14}, key="days"),
        b.add("NumberInput", {"label": "Total budget (EUR)", "value": {"$bindState": "/prefs/budget"},
                              "min": 50, "max": 100000}, key="budget"),
        b.add("Select", {"label": "Travel style", "value": {"$bindState": "/prefs/style"},
                         "options": TRAVEL_STYLES}, key="style"),
        b.add("TextInput", {"label": "Interests", "value": {"$bindState": "/prefs/interests"},
                            "placeholder": "food, history, nightlife..."}, key="interests"),
    ]
    submit = b.add("Button", {"label": "Plan my trip", "variant": "primary"}, key="submit",
                   on={"press": {"action": "submitPreferences"}})
    intro = b.add("Text", {"text": "A few details and I'll build your itinerary.", "tone": "muted"})
    card = b.add("Card", {"title": f"Trip to {req.destination}", "subtitle": "Your preferences"},
                 [intro, *fields, submit], key="prefs-form")
    base = defaults.model_dump() if defaults else {"budget": 1000, "style": "balanced",
                                                   "interests": ""}
    initial = {"prefs": {**base, "destination": req.destination, "days": req.days}}
    return b.spec(card, state=initial)


def itinerary(prefs: Preferences, plan: TripPlan) -> Spec:
    b = _Builder()
    total = plan.total_cost()
    remaining = prefs.budget - total

    heading = b.add("Heading", {"text": f"{prefs.days} days in {prefs.destination}", "level": 1})
    summary = b.add("Text", {"text": plan.summary, "tone": "muted"})
    stats = b.add("Stack", {"direction": "horizontal", "gap": "md"}, [
        b.add("Stat", {"label": "Estimated cost", "value": _money(total)}),
        b.add("Stat", {"label": "Budget", "value": _money(prefs.budget)}),
        b.add("Stat", {"label": "Left over" if remaining >= 0 else "Over budget",
                       "value": _money(abs(remaining))}),
        b.add("Stat", {"label": "Style", "value": prefs.style.title()}),
    ])
    days = b.add("Stack", {"direction": "vertical", "gap": "md"}, [
        b.add("DayCard", {"day": d.day, "title": d.title,
                          "activities": [a.model_dump() for a in d.activities]})
        for d in plan.days
    ])

    by_cat = plan.cost_by_category()
    chart = b.add("BarChart", {"title": "Spend by category", "unit": "€",
                               "data": [{"label": k, "value": v} for k, v in by_cat.items()]})
    table = b.add("Table", {
        "columns": ["Day", "Activities", "Cost"],
        "rows": [[f"Day {d.day}", str(len(d.activities)),
                  _money(sum(a.cost for a in d.activities))] for d in plan.days]
                + [["Total", str(sum(len(d.activities) for d in plan.days)), _money(total)]],
    })
    budget = b.add("Card", {"title": "Budget breakdown", "subtitle": None}, [chart, table])

    # Optional sections: rendered only when the model chose to include them.
    extras = []
    if plan.tips:
        extras.append(b.add("BulletList", {"title": "Local tips", "items": plan.tips}))
    if plan.packing_list:
        extras.append(b.add("BulletList", {"title": "Packing list", "items": plan.packing_list}))

    replan = b.add("Button", {"label": "Change preferences", "variant": "secondary"},
                   on={"press": {"action": "replan"}}, key="replan")
    root = b.add("Stack", {"direction": "vertical", "gap": "lg"},
                 [heading, summary, stats, days, budget, *extras, replan], key="itinerary")
    return b.spec(root)
