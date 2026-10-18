import { describe, expect, it } from "vitest";

import { parseEditors } from "./CollectionForm";

describe("parseEditors", () => {
  it("splits nicknames by commas, spaces and new lines", () => {
    expect(parseEditors("Alex_UA, steve\n  herobrine ,,")).toEqual([
      "Alex_UA",
      "steve",
      "herobrine",
    ]);
  });

  it("returns an empty list for an empty field", () => {
    expect(parseEditors()).toEqual([]);
    expect(parseEditors("  ,  ")).toEqual([]);
  });
});
