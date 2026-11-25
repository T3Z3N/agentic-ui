/** Contract tests: specs produced by the Python backend must satisfy the Zod catalog. */
import { describe, expect, it } from "vitest";
import form from "../../../shared/fixtures/preferences-form.json";
import itinerary from "../../../shared/fixtures/itinerary.json";
import exported from "../../../shared/catalog.schema.json";
import { catalog } from "./catalog";
import { specIssues } from "./validate";

const clone = <T,>(x: T): T => structuredClone(x);

describe("backend ↔ frontend contract", () => {
  it.each([["preferences-form", form], ["itinerary", itinerary]])("%s fixture is valid", (_, spec) => {
    expect(specIssues(spec)).toEqual([]);
  });

  it("exported catalog is up to date (run `npm run export-catalog` if this fails)", () => {
    expect(exported.componentNames).toEqual(catalog.componentNames);
    expect(exported.actionNames).toEqual(catalog.actionNames);
  });
});

describe("specIssues", () => {
  it("flags unknown component types", () => {
    const s = clone(form) as any;
    s.elements.submit.type = "Script";
    expect(specIssues(s)).not.toEqual([]);
  });

  it("flags missing root and dangling children", () => {
    const s = clone(form) as any;
    s.root = "ghost";
    s.elements["prefs-form"].children.push("nope");
    const issues = specIssues(s).join("\n");
    expect(issues).toContain('root "ghost"');
    expect(issues).toContain('child "nope"');
  });

  it("flags nested prop errors", () => {
    const s = clone(itinerary) as any;
    const day = Object.values(s.elements).find((e: any) => e.type === "DayCard") as any;
    day.props.activities[0].category = "casino";
    expect(specIssues(s).join()).toMatch(/DayCard.*activities\.0\.category/);
  });

  it("flags unknown actions but allows built-ins", () => {
    const s = clone(form) as any;
    s.elements.submit.on = { press: { action: "setState" } };
    expect(specIssues(s)).toEqual([]);
    s.elements.submit.on = { press: { action: "deleteAccount" } };
    expect(specIssues(s).join()).toContain("deleteAccount");
  });

  it("rejects non-objects", () => {
    expect(specIssues(null)).not.toEqual([]);
    expect(specIssues("hi")).not.toEqual([]);
  });
});
