import { describe, expect, it } from "vitest";
import { parseUtcDateFromFilename, formatDateForInput } from "./dateUtils.js";

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
