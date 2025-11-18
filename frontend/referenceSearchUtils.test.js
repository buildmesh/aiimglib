import { describe, expect, it } from "vitest";
import { resetReferenceSearchState } from "./referenceSearchUtils.js";

describe("resetReferenceSearchState", () => {
  it("trims the query and resets the page", () => {
    const state = { page: 3, currentQuery: "old" };
    resetReferenceSearchState(state, "  new query  ");
    expect(state.page).toBe(1);
    expect(state.currentQuery).toBe("new query");
  });

  it("handles undefined query", () => {
    const state = { page: 2, currentQuery: "old" };
    resetReferenceSearchState(state);
    expect(state.page).toBe(1);
    expect(state.currentQuery).toBe("");
  });
});
