"""Domain models. The LLM fills these via structured output; it never writes UI."""

from typing import Literal

from pydantic import BaseModel, Field

TravelStyle = Literal["budget", "balanced", "luxury"]
Category = Literal["food", "sight", "activity", "transport", "stay"]

TRAVEL_STYLES: list[str] = ["budget", "balanced", "luxury"]


class TripRequest(BaseModel):
    """What the user asked for, extracted from free text."""

    destination: str = Field(description="City or region the user wants to visit")
    days: int = Field(ge=1, le=14, description="Trip length in days (default 3)")


class Preferences(BaseModel):
    """Filled in by the user through the agent-generated form (human-in-the-loop)."""

    destination: str = Field(min_length=1)
    days: int = Field(ge=1, le=14)
    budget: int = Field(ge=50, le=100_000, description="Total budget in EUR")
    style: TravelStyle = "balanced"
    interests: str = ""


class Activity(BaseModel):
    time: str = Field(description="e.g. 09:00")
    name: str
    category: Category
    cost: float = Field(ge=0, description="Estimated cost in EUR")


class DayPlan(BaseModel):
    day: int = Field(ge=1)
    title: str
    activities: list[Activity] = Field(min_length=1)


class TripPlan(BaseModel):
    """The agent's plan. Optional sections let the model decide what UI appears."""

    summary: str
    days: list[DayPlan] = Field(min_length=1)
    tips: list[str] = Field(default_factory=list, description="Local tips; empty if none")
    packing_list: list[str] = Field(default_factory=list, description="Empty unless useful")

    def total_cost(self) -> float:
        return round(sum(a.cost for d in self.days for a in d.activities), 2)

    def cost_by_category(self) -> dict[str, float]:
        totals: dict[str, float] = {}
        for d in self.days:
            for a in d.activities:
                totals[a.category] = round(totals.get(a.category, 0) + a.cost, 2)
        return dict(sorted(totals.items(), key=lambda kv: -kv[1]))
