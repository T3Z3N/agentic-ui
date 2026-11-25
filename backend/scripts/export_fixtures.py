"""Write real backend-generated specs to shared/fixtures for the frontend contract test."""

import json
from pathlib import Path

from travel_agent import ui
from travel_agent.llm import FakePlanner
from travel_agent.models import Preferences, TripRequest

out = Path(__file__).resolve().parents[2] / "shared" / "fixtures"
out.mkdir(parents=True, exist_ok=True)
prefs = Preferences(destination="Porto", days=2, budget=600, style="budget", interests="wine")
specs = {
    "preferences-form": ui.preferences_form(TripRequest(destination="Porto", days=2)),
    "itinerary": ui.itinerary(prefs, FakePlanner().plan(prefs)),
}
for name, spec in specs.items():
    (out / f"{name}.json").write_text(json.dumps(spec, indent=2, ensure_ascii=False) + "\n")
print(f"wrote {len(specs)} fixtures to {out}")
