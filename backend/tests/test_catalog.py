import copy

import pytest

from travel_agent.catalog import SpecValidationError, load_catalog, spec_issues, validate_spec

VALID = {
    "root": "card",
    "elements": {
        "card": {"type": "Card", "props": {"title": "Hi", "subtitle": None}, "children": ["btn"]},
        "btn": {"type": "Button", "props": {"label": "Go", "variant": "primary"}, "children": [],
                "on": {"press": {"action": "submitPreferences"}}},
    },
    "state": {"prefs": {}},
}


def mutate(fn):
    spec = copy.deepcopy(VALID)
    fn(spec)
    return spec


def test_catalog_matches_frontend_export():
    cat = load_catalog()
    assert "DayCard" in cat["componentNames"]
    assert set(cat["components"]) == set(cat["componentNames"])
    assert {"submitPreferences", "replan"} <= set(cat["actionNames"])


def test_valid_spec_passes():
    assert spec_issues(VALID) == []
    assert validate_spec(VALID) is VALID


def test_builtin_actions_are_allowed():
    spec = mutate(lambda s: s["elements"]["btn"].update(on={"press": [{"action": "setState"}]}))
    assert spec_issues(spec) == []


@pytest.mark.parametrize("breaker, expected", [
    (lambda s: s["elements"]["card"].update(type="Marquee"), "Marquee"),
    (lambda s: s.update(root="nope"), "root 'nope'"),
    (lambda s: s["elements"]["card"].update(children=["ghost"]), "child 'ghost'"),
    (lambda s: s["elements"]["btn"]["props"].pop("label"), "'label' is a required property"),
    (lambda s: s["elements"]["btn"]["props"].update(variant="huge"), "huge"),
    (lambda s: s["elements"]["btn"].update(on={"press": {"action": "rm -rf"}}), "unknown action"),
    (lambda s: s.update(state=[1, 2]), "must be an object"),
    (lambda s: s.pop("elements"), "'elements' is a required property"),
    (lambda s: s["elements"]["card"].update(onclick="alert(1)"), "Additional properties"),
])
def test_invalid_specs_are_rejected(breaker, expected):
    issues = spec_issues(mutate(breaker))
    assert any(expected in i for i in issues), issues


def test_validate_spec_raises_with_issue_list():
    with pytest.raises(SpecValidationError) as exc:
        validate_spec(mutate(lambda s: s.update(root="nope")))
    assert exc.value.issues


def test_missing_catalog_file_has_helpful_error(tmp_path):
    with pytest.raises(FileNotFoundError, match="export-catalog"):
        load_catalog(str(tmp_path / "missing.json"))


def test_nested_prop_validation():
    spec = {"root": "d", "elements": {"d": {"type": "DayCard", "children": [], "props": {
        "day": 1, "title": "x",
        "activities": [{"time": "9", "name": "a", "category": "spa", "cost": -1}]}}}}
    issues = spec_issues(spec)
    assert any("spa" in i for i in issues) and any("-1" in i for i in issues)
