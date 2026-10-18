import { describe, expect, it } from "vitest";

import { catalogHref, parseFilters, toApiQuery, toggle, withProfileDefaults } from "./filters";

describe("parseFilters", () => {
  it("reads the query string with safe defaults", () => {
    const filters = parseFilters({
      type: "shader",
      game_version: "26.3",
      category: "cartoon,realistic",
      page: "3",
      all: "1",
    });

    expect(filters).toMatchObject({
      type: "shader",
      game_version: "26.3",
      categories: ["cartoon", "realistic"],
      page: 3,
      all: true,
    });
  });

  it("falls back to mods and page 1 for junk", () => {
    expect(parseFilters({ type: "plugin", page: "-5" })).toMatchObject({ type: "mod", page: 1 });
  });
});

describe("withProfileDefaults", () => {
  const profile = { game_version: "26.3", loader: "fabric" };

  it("fills version and loader from the game profile", () => {
    const { filters, fromProfile } = withProfileDefaults(parseFilters({}), profile);

    expect(fromProfile).toBe(true);
    expect(filters.game_version).toBe("26.3");
    expect(filters.loader).toBe("fabric");
  });

  it("keeps what the URL says and skips the loader for shaders", () => {
    const { filters } = withProfileDefaults(
      parseFilters({ type: "shader", game_version: "1.21.1" }),
      profile,
    );

    expect(filters.game_version).toBe("1.21.1");
    expect(filters.loader).toBe("");
  });

  it("does nothing with «show all», for guests or vanilla players", () => {
    expect(withProfileDefaults(parseFilters({ all: "1" }), profile).fromProfile).toBe(false);
    expect(withProfileDefaults(parseFilters({}), null).fromProfile).toBe(false);
    expect(
      withProfileDefaults(parseFilters({}), { game_version: "", loader: "vanilla" }).fromProfile,
    ).toBe(false);
  });
});

describe("toApiQuery", () => {
  it("sends only filters that apply to the type", () => {
    const filters = parseFilters({
      type: "resourcepack",
      loader: "fabric",
      gpu_load: "light",
      category: "vanilla-like",
    });

    expect(toApiQuery(filters)).toEqual({
      type: "resourcepack",
      page: 1,
      category: "vanilla-like",
    });
  });
});

describe("catalogHref", () => {
  it("builds a clean URL and resets the page", () => {
    const filters = parseFilters({ type: "mod", loader: "fabric", page: "4" });

    expect(catalogHref(filters, { game_version: "26.3" })).toBe(
      "/mods?game_version=26.3&loader=fabric",
    );
    expect(catalogHref(parseFilters({}))).toBe("/mods");
  });

  it("toggles categories", () => {
    expect(toggle(["a", "b"], "a")).toEqual(["b"]);
    expect(toggle(["a"], "b")).toEqual(["a", "b"]);
  });
});
