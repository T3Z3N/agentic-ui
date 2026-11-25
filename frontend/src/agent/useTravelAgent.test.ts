import type { Message } from "@ag-ui/client";
import { describe, expect, it } from "vitest";
import { toChatLines } from "./useTravelAgent";

describe("toChatLines", () => {
  it("keeps user/assistant text and drops tool/system/empty messages", () => {
    const msgs = [
      { id: "1", role: "system", content: "sys" },
      { id: "2", role: "user", content: "Plan 3 days in Lisbon" },
      { id: "3", role: "assistant", content: "" },
      { id: "4", role: "tool", content: "{}", toolCallId: "t" },
      { id: "5", role: "assistant", content: "Fill in the form" },
    ] as Message[];
    expect(toChatLines(msgs)).toEqual([
      { id: "2", role: "user", text: "Plan 3 days in Lisbon" },
      { id: "5", role: "assistant", text: "Fill in the form" },
    ]);
  });

  it("handles an empty history", () => {
    expect(toChatLines([])).toEqual([]);
  });
});
