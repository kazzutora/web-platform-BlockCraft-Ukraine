import { describe, expect, it } from "vitest";

import { plural } from "./plural";

const mods = { one: "мод", few: "моди", many: "модів" };

describe("plural", () => {
  it.each([
    [1, "1 мод"],
    [2, "2 моди"],
    [4, "4 моди"],
    [5, "5 модів"],
    [11, "11 модів"],
    [21, "21 мод"],
    [22, "22 моди"],
    [0, "0 модів"],
  ])("%i → %s", (count, expected) => {
    expect(plural(count, mods)).toBe(expected);
  });

  it("groups thousands the Ukrainian way", () => {
    expect(plural(1285, mods)).toMatch(/^1\s285 модів$/);
  });
});
