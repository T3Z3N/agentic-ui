import { expect, test } from "@playwright/test";

test("chat → agent-generated form → agent-generated itinerary → replan", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Generative UI canvas" })).toBeVisible();

  await page.getByLabel("Message").fill("Plan 2 days in Porto");
  await page.getByRole("button", { name: "Send" }).click();

  // Turn 1: the agent answers with a form (human-in-the-loop), pre-filled from its state.
  const canvas = page.getByRole("main", { name: "Generated interface" });
  await expect(canvas.getByLabel("Destination")).toHaveValue("Porto");
  await expect(canvas.getByLabel("Days")).toHaveValue("2");
  await expect(page.locator(".msg.assistant").last()).toContainText("2 days in Porto");

  await canvas.getByLabel("Total budget (EUR)").fill("1500");
  await canvas.getByLabel("Travel style").selectOption("luxury");
  await canvas.getByLabel("Interests").fill("seafood");
  await canvas.getByRole("button", { name: "Plan my trip" }).click();

  // Turn 2: the edited preferences reach the agent through AG-UI shared state.
  await expect(canvas.getByRole("heading", { name: "2 days in Porto" })).toBeVisible();
  await expect(canvas.getByTestId("day-card")).toHaveCount(2);
  await expect(canvas.getByTestId("stat").filter({ hasText: "Budget" })).toContainText("€1,500");
  await expect(canvas.getByTestId("stat").filter({ hasText: "Style" })).toContainText("Luxury");
  await expect(canvas.getByText("focused on seafood")).toBeVisible();
  await expect(canvas.getByRole("figure", { name: "Spend by category" })).toBeVisible();

  // Turn 3: "Change preferences" brings the form back pre-filled with the last trip.
  await canvas.getByRole("button", { name: "Change preferences" }).click();
  await expect(canvas.getByRole("button", { name: "Plan my trip" })).toBeVisible();
  await expect(canvas.getByLabel("Destination")).toHaveValue("Porto");
  await expect(canvas.getByLabel("Total budget (EUR)")).toHaveValue("1500");
  await expect(canvas.getByLabel("Travel style")).toHaveValue("luxury");
  await expect(page.locator(".msg.user")).toHaveCount(3);

  // Turn 4: a new chat request starts a new trip instead of re-planning the old one.
  await page.getByLabel("Message").fill("Plan 4 days in Rome");
  await page.getByRole("button", { name: "Send" }).click();
  await expect(canvas.getByLabel("Destination")).toHaveValue("Rome");
  await expect(canvas.getByLabel("Days")).toHaveValue("4");
});

test("suggestion chips start a conversation", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Plan 3 days in Lisbon" }).click();
  await expect(page.getByRole("main").getByLabel("Destination")).toHaveValue("Lisbon");
});

test("shows an error when the agent is unreachable", async ({ page }) => {
  await page.route("**/agent", (route) => route.abort());
  await page.goto("/");
  await page.getByLabel("Message").fill("Plan 2 days in Porto");
  await page.getByRole("button", { name: "Send" }).click();
  await expect(page.getByRole("alert")).toContainText("Agent error");
  await expect(page.getByLabel("Message")).toBeEnabled();
});
