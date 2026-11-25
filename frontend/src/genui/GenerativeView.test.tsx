import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { Spec } from "@json-render/react";
import { describe, expect, it, vi } from "vitest";
import form from "../../../shared/fixtures/preferences-form.json";
import itinerary from "../../../shared/fixtures/itinerary.json";
import { GenerativeView } from "./GenerativeView";

const setup = (spec: unknown) => {
  const onSubmitPreferences = vi.fn();
  const onReplan = vi.fn();
  render(<GenerativeView spec={spec as Spec} onSubmitPreferences={onSubmitPreferences} onReplan={onReplan} />);
  return { onSubmitPreferences, onReplan, user: userEvent.setup() };
};

describe("GenerativeView – preferences form (backend fixture)", () => {
  it("seeds the inputs from spec.state", () => {
    setup(form);
    expect(screen.getByLabelText("Destination")).toHaveValue("Porto");
    expect(screen.getByLabelText("Days")).toHaveValue(2);
    expect(screen.getByLabelText("Total budget (EUR)")).toHaveValue(1000);
    expect(screen.getByLabelText("Travel style")).toHaveValue("balanced");
  });

  it("submits the values the user edited", async () => {
    const { onSubmitPreferences, user } = setup(form);
    const budget = screen.getByLabelText("Total budget (EUR)");
    await user.clear(budget);
    await user.type(budget, "1500");
    await user.selectOptions(screen.getByLabelText("Travel style"), "luxury");
    await user.type(screen.getByLabelText("Interests"), "seafood");
    await user.click(screen.getByRole("button", { name: "Plan my trip" }));
    expect(onSubmitPreferences).toHaveBeenCalledWith({
      destination: "Porto", days: 2, budget: 1500, style: "luxury", interests: "seafood",
    });
  });
});

describe("GenerativeView – re-sent snapshots (regression)", () => {
  // AG-UI can deliver the same ui_spec several times as new objects (one STATE_SNAPSHOT
  // per node + a final one). json-render's ActionProvider captures `handlers` on first
  // mount, so a store rebuilt per object identity made submit read stale values.
  const view = (spec: unknown, onSubmitPreferences = vi.fn()) => (
    <GenerativeView spec={spec as Spec} onSubmitPreferences={onSubmitPreferences} onReplan={vi.fn()} />
  );

  it("keeps edits and submits them when an identical spec arrives as a new object", async () => {
    const onSubmit = vi.fn();
    const { rerender } = render(view(structuredClone(form), onSubmit));
    rerender(view(structuredClone(form), onSubmit));
    const user = userEvent.setup();
    const budget = screen.getByLabelText("Total budget (EUR)");
    await user.clear(budget);
    await user.type(budget, "700");
    rerender(view(structuredClone(form), onSubmit)); // another duplicate mid-edit
    expect(screen.getByLabelText("Total budget (EUR)")).toHaveValue(700);
    await user.click(screen.getByRole("button", { name: "Plan my trip" }));
    expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({ budget: 700 }));
  });

  it("uses the new spec's state when the agent sends a different form", async () => {
    const onSubmit = vi.fn();
    const { rerender } = render(view(form, onSubmit));
    const other = structuredClone(form) as any;
    other.state.prefs.destination = "Kyoto";
    rerender(view(other, onSubmit));
    await userEvent.setup().click(screen.getByRole("button", { name: "Plan my trip" }));
    expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({ destination: "Kyoto" }));
  });
});

describe("GenerativeView – itinerary (backend fixture)", () => {
  it("renders days, stats, chart and table", () => {
    setup(itinerary);
    expect(screen.getByRole("heading", { name: "2 days in Porto" })).toBeInTheDocument();
    expect(screen.getAllByTestId("day-card")).toHaveLength(2);
    expect(screen.getAllByTestId("stat")).toHaveLength(4);
    expect(screen.getByRole("figure", { name: "Spend by category" })).toBeInTheDocument();
    const table = screen.getByRole("table");
    expect(within(table).getByText("Total")).toBeInTheDocument();
    expect(screen.getByText("Local tips")).toBeInTheDocument();
  });

  it("wires the replan button to the replan action", async () => {
    const { onReplan, user } = setup(itinerary);
    await user.click(screen.getByRole("button", { name: "Change preferences" }));
    expect(onReplan).toHaveBeenCalledOnce();
  });
});

describe("GenerativeView – untrusted specs", () => {
  it("refuses components outside the catalog", () => {
    setup({ root: "x", elements: { x: { type: "IFrame", props: { src: "https://evil" }, children: [] } } });
    expect(screen.getByRole("alert")).toHaveTextContent("can't render");
  });

  it("refuses wrong prop types", () => {
    setup({ root: "x", elements: { x: { type: "Stat", props: { label: 1, value: "a" }, children: [] } } });
    expect(screen.getByRole("alert")).toBeInTheDocument();
  });
});
