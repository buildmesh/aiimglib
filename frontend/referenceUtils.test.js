import { describe, expect, it } from "vitest";
import { buildPromptMeta, shouldAutoFillThumbnail, getFirstReferenceAsset } from "./referenceUtils.js";

describe("buildPromptMeta", () => {
  it("returns string when no references", () => {
    expect(buildPromptMeta("hello", [])).toBe("hello");
  });

  it("returns null when prompt empty and no refs", () => {
    expect(buildPromptMeta("", null)).toBeNull();
  });

  it("embeds references followed by prompt", () => {
    const refs = [{ id: "abc", prompt_text: "foo" }, { id: "def" }];
    const meta = buildPromptMeta("final prompt", refs);
    expect(meta).toEqual([{ id: "abc" }, { id: "def" }, "final prompt"]);
  });
});

describe("shouldAutoFillThumbnail", () => {
  it("returns false for images", () => {
    expect(shouldAutoFillThumbnail("image", [{ id: "x", thumbnail_file: "thumb.png" }])).toBe(false);
  });

  it("returns true for videos with reference assets", () => {
    const result = shouldAutoFillThumbnail("video", [{ id: "x", thumbnail_file: "thumb.png" }]);
    expect(result).toBe(true);
  });

  it("returns false when references missing assets", () => {
    const result = shouldAutoFillThumbnail("video", [{ id: "x" }]);
    expect(result).toBe(false);
  });
});

describe("getFirstReferenceAsset", () => {
  it("returns null when no references", () => {
    expect(getFirstReferenceAsset([])).toBeNull();
  });

  it("prefers thumbnail file when available", () => {
    const asset = getFirstReferenceAsset([{ id: "x", thumbnail_file: "thumb.png", file_name: "main.png" }]);
    expect(asset).toEqual({ thumbnail: "thumb.png", file: "main.png" });
  });

  it("falls back to first reference with file", () => {
    const asset = getFirstReferenceAsset([{ id: "x" }, { id: "y", file_name: "foo.png" }]);
    expect(asset).toEqual({ thumbnail: null, file: "foo.png" });
  });
});
