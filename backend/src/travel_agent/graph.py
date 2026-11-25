"""LangGraph agent. Graph state is shared with the browser over AG-UI:
the frontend writes `preferences` / `edit_preferences`, the agent writes `ui_spec`
(a json-render spec) and remembers `last_preferences`.

    START -> route --(edit_preferences)--> edit_preferences -> END   (no LLM call)
                   |-(preferences)-------> plan_trip --------> END
                   \\-(otherwise)---------> ask_preferences --> END
"""

import logging
from typing import Annotated, Any, Literal, TypedDict

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from pydantic import ValidationError

from . import ui
from .llm import Planner, get_planner
from .models import Preferences, TripRequest

log = logging.getLogger(__name__)


class TravelState(TypedDict, total=False):
    messages: Annotated[list[AnyMessage], add_messages]
    preferences: dict[str, Any] | None  # written by the UI form
    edit_preferences: bool  # written by the UI "Change preferences" button
    last_preferences: dict[str, Any] | None  # what the current itinerary was built from
    ui_spec: dict[str, Any] | None  # written by the agent, rendered by json-render


def _last_user_text(state: TravelState) -> str:
    for m in reversed(state.get("messages") or []):
        if isinstance(m, HumanMessage):
            c = m.content
            return c if isinstance(c, str) else " ".join(
                p.get("text", "") for p in c if isinstance(p, dict))
    return ""


def _error_spec(title: str, detail: str) -> dict[str, Any]:
    return {"root": "error", "elements": {
        "error": {"type": "Card", "props": {"title": title, "subtitle": None}, "children": ["msg"]},
        "msg": {"type": "Text", "props": {"text": detail, "tone": "muted"}, "children": []},
    }}


def build_graph(planner: Planner | None = None, checkpointer: Any = None):
    planner = planner or get_planner()

    def route(state: TravelState) -> Literal["edit_preferences", "plan_trip", "ask_preferences"]:
        if state.get("edit_preferences") and state.get("last_preferences"):
            return "edit_preferences"
        return "plan_trip" if state.get("preferences") else "ask_preferences"

    def edit_preferences(state: TravelState) -> TravelState:
        last = Preferences.model_validate(state["last_preferences"])
        return {
            "messages": [AIMessage(content="Sure, tweak anything and I'll re-plan.")],
            "edit_preferences": False,
            "preferences": None,
            "ui_spec": ui.preferences_form(
                TripRequest(destination=last.destination, days=last.days), defaults=last),
        }

    def ask_preferences(state: TravelState) -> TravelState:
        text = _last_user_text(state) or "Plan a trip"
        try:
            req = planner.parse_request(text)
        except Exception as exc:  # LLM down / bad output: degrade, don't crash the run
            log.exception("parse_request failed")
            return {"messages": [AIMessage(content="Sorry, I couldn't reach the model.")],
                    "ui_spec": _error_spec("Model unavailable", str(exc))}
        return {
            "edit_preferences": False,
            "messages": [AIMessage(content=f"Great, {req.days} days in {req.destination}! "
                                           "Fill in the form so I can tailor the plan.")],
            "ui_spec": ui.preferences_form(req),
        }

    def plan_trip(state: TravelState) -> TravelState:
        try:
            prefs = Preferences.model_validate(state["preferences"])
        except ValidationError as exc:
            issues = "; ".join(f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in exc.errors())
            return {"messages": [AIMessage(content=f"Some preferences look off: {issues}")],
                    "preferences": None,
                    "ui_spec": _error_spec("Invalid preferences", issues)}
        try:
            plan = planner.plan(prefs)
        except Exception as exc:
            log.exception("plan failed")
            return {"messages": [AIMessage(content="Sorry, planning failed. Try again.")],
                    "ui_spec": _error_spec("Planning failed", str(exc))}
        return {
            "messages": [AIMessage(content=f"{plan.summary} Estimated total: "
                                           f"€{plan.total_cost():,.0f}.")],
            "ui_spec": ui.itinerary(prefs, plan),
            # Consume the submission: a new chat message starts a new trip instead of
            # silently re-planning this one. Keep it for "Change preferences".
            "preferences": None,
            "last_preferences": prefs.model_dump(),
        }

    g = StateGraph(TravelState)
    g.add_node("ask_preferences", ask_preferences)
    g.add_node("plan_trip", plan_trip)
    g.add_node("edit_preferences", edit_preferences)
    g.add_conditional_edges(START, route)
    g.add_edge("ask_preferences", END)
    g.add_edge("plan_trip", END)
    g.add_edge("edit_preferences", END)
    # The AG-UI bridge reads graph state between runs, so it needs a checkpointer.
    return g.compile(checkpointer=checkpointer or MemorySaver())
