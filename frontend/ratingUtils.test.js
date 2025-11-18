import { describe, expect, it } from "vitest";
import { computeStarFills } from "./ratingUtils.js";

describe("computeStarFills", () => {
  it("handles whole numbers", () => {
    expect(computeStarFills(3)).toEqual([100, 100, 100, 0, 0]);
  });

  it("handles partial stars", () => {
    expect(computeStarFills(2.6)).toEqual([100, 100, 60, 0, 0]);
  });

  it("clamps values outside range", () => {
    expect(computeStarFills(-1)).toEqual([0, 0, 0, 0, 0]);
    expect(computeStarFills(6)).toEqual([100, 100, 100, 100, 100]);
  });
});
