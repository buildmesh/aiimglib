import { describe, expect, it } from "vitest";
import { parseUtcDateFromFilename, formatDateForInput, formatDisplayDate } from "./dateUtils.js";

const testCases = [
  { name: "2025-11-15_01-50-03.png", expectedIso: "2025-11-15T01:50:03.000Z" },
  { name: "2025-11-15T015003.png", expectedIso: "2025-11-15T01:50:03.000Z" },
  { name: "1763171403.png", expectedIso: "2025-11-15T01:50:03.000Z" },
  { name: "1763171403000.png", expectedIso: "2025-11-15T01:50:03.000Z" },
];

describe("parseUtcDateFromFilename", () => {
  testCases.forEach(({ name, expectedIso }) => {
    it(`parses ${name}`, () => {
      const date = parseUtcDateFromFilename(name);
      expect(date?.toISOString()).toBe(expectedIso);
    });
  });
});

describe("formatDateForInput", () => {
  it("formats date for input field", () => {
    const date = new Date("2025-11-15T01:50:03Z");
    const formatted = formatDateForInput(date);
    expect(formatted).toBe("2025-11-15T01:50");
  });
});

describe("formatDisplayDate", () => {
  it("returns friendly text", () => {
    expect(formatDisplayDate("2025-11-15T01:50:03Z")).toContain("2025");
  });

  it("handles invalid dates", () => {
    expect(formatDisplayDate("not-a-date")).toBe("Date unknown");
  });
});
