"""LLM access behind a tiny interface, so the graph never cares which model runs.

LLM_PROVIDER=ollama (default) -> ChatOllama structured output (local, free)
LLM_PROVIDER=fake             -> deterministic planner for tests / offline demos
"""

import os
import re
from typing import Protocol

from langchain_core.prompts import ChatPromptTemplate

from .models import Activity, DayPlan, Preferences, TripPlan, TripRequest


class Planner(Protocol):
    def parse_request(self, text: str) -> TripRequest: ...
    def plan(self, prefs: Preferences) -> TripPlan: ...


REQUEST_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "Extract the travel destination and trip length in days from the user's "
               "message. If no length is given use 3. If no destination is given use 'Lisbon'."),
    ("human", "{text}"),
])

PLAN_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "You are an expert travel planner. Build a realistic day-by-day itinerary.\n"
     "- Exactly {days} days, numbered from 1, each with 3-5 activities in time order.\n"
     "- Times use 24-hour HH:MM format, e.g. 09:00 or 19:30.\n"
     "- Use real places in {destination}. Costs are realistic per-person prices in EUR.\n"
     "- Every day ends with one 'stay' activity: that night's accommodation and its price.\n"
     "- The whole trip should cost roughly 70-100% of the {budget} EUR budget "
     "for a {style} traveller, never more.\n"
     "- Only include tips or a packing list if they are genuinely useful; otherwise leave them empty."),
    ("human", "Destination: {destination}\nDays: {days}\nBudget: {budget} EUR\n"
              "Style: {style}\nInterests: {interests}"),
])


# Planner calls produce JSON for the program, not prose for the user. This metadata
# tells the AG-UI LangGraph bridge not to stream their tokens as chat messages.
INTERNAL_LLM_CONFIG = {"metadata": {"emit-messages": False, "emit-tool-calls": False}}


class OllamaPlanner:
    def __init__(self, model: str | None = None, base_url: str | None = None):
        from langchain_ollama import ChatOllama

        llm = ChatOllama(
            model=model or os.environ.get("OLLAMA_MODEL", "llama3.1:8b"),
            base_url=base_url or os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
            temperature=0.2,
        )
        # Ollama constrains decoding to the Pydantic JSON schema.
        self._request = (REQUEST_PROMPT | llm.with_structured_output(TripRequest, method="json_schema")
                         ).with_config(INTERNAL_LLM_CONFIG)
        self._plan = (PLAN_PROMPT | llm.with_structured_output(TripPlan, method="json_schema")
                      ).with_config(INTERNAL_LLM_CONFIG)

    def parse_request(self, text: str) -> TripRequest:
        return self._request.invoke({"text": text})

    def plan(self, prefs: Preferences) -> TripPlan:
        return tidy_plan(self._plan.invoke(prefs.model_dump()), prefs)


_TIME = re.compile(r"(\d{1,2})(?:[:.h](\d{2}))?\s*([ap])?\.?\s*m?\.?", re.I)


def normalize_time(raw: str) -> str:
    """'9:00 AM' / ': 12:00 PM' / '7pm' / '19h30' -> '09:00' / '12:00' / '19:00' / '19:30'.
    Returns the stripped input unchanged if it contains no recognisable time."""
    m = _TIME.search(raw)
    if not m:
        return raw.strip()
    hour, minute, ampm = int(m.group(1)), int(m.group(2) or 0), (m.group(3) or "").lower()
    if ampm == "p" and hour < 12:
        hour += 12
    elif ampm == "a" and hour == 12:
        hour = 0
    if hour > 23 or minute > 59:
        return raw.strip()
    return f"{hour:02d}:{minute:02d}"


def tidy_plan(plan: TripPlan, prefs: Preferences) -> TripPlan:
    """Deterministic clean-up of small-model quirks: trust the user's day count,
    renumber days, normalise times and keep activities in time order."""
    days = []
    for i, d in enumerate(plan.days[: prefs.days]):
        acts = [a.model_copy(update={"time": normalize_time(a.time)}) for a in d.activities]
        acts.sort(key=lambda a: a.time)
        days.append(d.model_copy(update={"day": i + 1, "activities": acts}))
    return plan.model_copy(update={"days": days})


class FakePlanner:
    """Deterministic stand-in: same contract, no network."""

    _DAYS = re.compile(r"(\d+)\s*(?:-|\s)?days?", re.I)
    _DEST = re.compile(r"\b(?:in|to|visit)\s+([A-Z][\w' -]*?)(?:\s+for\b|[.,!?]|$)")

    def parse_request(self, text: str) -> TripRequest:
        days = self._DAYS.search(text)
        dest = self._DEST.search(text)
        return TripRequest(
            destination=dest.group(1).strip() if dest else "Lisbon",
            days=min(max(int(days.group(1)), 1), 14) if days else 3,
        )

    def plan(self, prefs: Preferences) -> TripPlan:
        per_day = prefs.budget / prefs.days
        days = [
            DayPlan(day=i, title=f"{prefs.destination} highlights, part {i}", activities=[
                Activity(time="09:00", name="Breakfast at a local café", category="food",
                         cost=round(per_day * 0.05)),
                Activity(time="10:30", name=f"Old town walking tour #{i}", category="sight",
                         cost=round(per_day * 0.10)),
                Activity(time="15:00", name="Museum or market visit", category="activity",
                         cost=round(per_day * 0.15)),
                Activity(time="20:00", name="Dinner", category="food", cost=round(per_day * 0.20)),
            ])
            for i in range(1, prefs.days + 1)
        ]
        tips = ["Buy a day transit pass", "Book popular sights a day ahead"]
        return TripPlan(
            summary=f"A {prefs.style} {prefs.days}-day trip to {prefs.destination}"
                    + (f" focused on {prefs.interests}." if prefs.interests else "."),
            days=days,
            tips=tips,
            packing_list=["Comfortable shoes"] if prefs.style != "luxury" else [],
        )


def get_planner() -> Planner:
    provider = os.environ.get("LLM_PROVIDER", "ollama").lower()
    if provider == "fake":
        return FakePlanner()
    if provider == "ollama":
        return OllamaPlanner()
    raise ValueError(f"Unknown LLM_PROVIDER {provider!r} (expected 'ollama' or 'fake')")
