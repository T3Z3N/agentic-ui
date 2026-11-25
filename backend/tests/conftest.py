import os

os.environ.setdefault("LLM_PROVIDER", "fake")  # never hit a real model in tests

import pytest

from travel_agent.models import Preferences, TripRequest


@pytest.fixture
def prefs() -> Preferences:
    return Preferences(destination="Porto", days=2, budget=600, style="budget", interests="wine")


@pytest.fixture
def req() -> TripRequest:
    return TripRequest(destination="Porto", days=2)
