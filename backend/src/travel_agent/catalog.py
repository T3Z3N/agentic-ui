"""Validates json-render specs against the catalog exported by the React app.

The frontend's Zod catalog is the source of truth; `npm run export-catalog`
writes shared/catalog.schema.json. Validating here means a bad spec is caught
on the server before it ever reaches a browser.
"""

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

DEFAULT_CATALOG_PATH = Path(__file__).resolve().parents[3] / "shared" / "catalog.schema.json"


class SpecValidationError(ValueError):
    def __init__(self, issues: list[str]):
        super().__init__("; ".join(issues))
        self.issues = issues


@lru_cache(maxsize=4)
def load_catalog(path: str | None = None) -> dict[str, Any]:
    p = Path(path or os.environ.get("CATALOG_PATH", DEFAULT_CATALOG_PATH))
    if not p.exists():
        raise FileNotFoundError(f"{p} not found - run `npm run export-catalog` in frontend/")
    return json.loads(p.read_text())


def spec_issues(spec: Any, catalog: dict[str, Any] | None = None) -> list[str]:
    """Return a list of human-readable problems (empty list = valid)."""
    catalog = catalog or load_catalog()
    # The renderer supports per-element `on` / `watch` bindings, but
    # catalog.jsonSchema() omits them, so strip them here and check them below.
    # Spec.state (initial state model) is also part of the core Spec type.
    shape = spec
    if isinstance(spec, dict) and "state" in spec and not isinstance(spec["state"], dict):
        return ["spec['state']: must be an object"]
    if isinstance(spec, dict) and isinstance(spec.get("elements"), dict):
        shape = {
            **{k: v for k, v in spec.items() if k != "state"},
            "elements": {
                k: {f: v for f, v in el.items() if f not in ("on", "watch")}
                if isinstance(el, dict) else el
                for k, el in spec["elements"].items()
            },
        }
    issues = [
        f"spec{''.join(f'[{p!r}]' for p in e.absolute_path)}: {e.message}"
        for e in Draft202012Validator(catalog["spec"]).iter_errors(shape)
    ]
    if issues:
        return issues

    elements: dict[str, Any] = spec["elements"]
    if spec["root"] not in elements:
        issues.append(f"root {spec['root']!r} is not in elements")

    actions = set(catalog["actionNames"]) | {"setState", "pushState", "removeState", "validateForm"}
    for key, el in elements.items():
        for child in el["children"]:
            if child not in elements:
                issues.append(f"{key}: child {child!r} does not exist")
        props_schema = catalog["components"][el["type"]]["props"]
        for e in Draft202012Validator(props_schema).iter_errors(el["props"]):
            path = ".".join(str(p) for p in e.absolute_path) or "props"
            issues.append(f"{key} ({el['type']}).{path}: {e.message}")
        for event, binding in (el.get("on") or {}).items():
            for b in binding if isinstance(binding, list) else [binding]:
                if b.get("action") not in actions:
                    issues.append(f"{key}: on.{event} uses unknown action {b.get('action')!r}")
    return issues


def validate_spec(spec: Any, catalog: dict[str, Any] | None = None) -> dict[str, Any]:
    issues = spec_issues(spec, catalog)
    if issues:
        raise SpecValidationError(issues)
    return spec
