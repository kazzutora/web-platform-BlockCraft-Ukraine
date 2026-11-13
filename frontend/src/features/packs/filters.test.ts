import { describe, expect, it } from "vitest";

import {
  catalogHref,
  nearestVersions,
  parseFilters,
  toApiQuery,
  withGameDefaults,
} from "./filters";

describe("pack catalog filters", () => {
  it("reads only known values from the URL", () => {
    const filters = parseFilters({
      version: "26.3",
      loader: "bukkit",
      origin: "modrinth",
      sort: "random",
      page: "3",
    });

    expect(filters).toMatchObject({
      gameVersion: "26.3",
      loader: "",
      origin: "modrinth",
      sort: "",
      page: 3,
      all: false,
    });
    expect(parseFilters({ version: "26w14a" }).gameVersion).toBe("");
  });

  it("takes «Моя гра» unless the URL or «усі версії» says otherwise", () => {
    const game = { game_version: "1.21.1", loader: "fabric" };

    expect(withGameDefaults(parseFilters({}), game)).toEqual({
      filters: expect.objectContaining({ gameVersion: "1.21.1", loader: "fabric" }),
      fromGame: true,
    });
    expect(withGameDefaults(parseFilters({ all: "1" }), game).fromGame).toBe(false);
    // A vanilla game has no pack loader: any loader of that version
    expect(
      withGameDefaults(parseFilters({}), { game_version: "1.21.1", loader: "vanilla" }).filters
        .loader,
    ).toBe("");
  });

  it("sends the game explicitly and keeps the rest optional", () => {
    expect(toApiQuery(parseFilters({ origin: "community" }))).toEqual({
      page: 1,
      game_version: "",
      loader: "",
      origin: "community",
    });
  });

  it("builds clean links and resets the page", () => {
    const filters = parseFilters({ version: "26.3", page: "4" });

    expect(catalogHref(filters, { loader: "quilt" })).toBe("/packs?version=26.3&loader=quilt");
    expect(catalogHref(parseFilters({}), { all: true })).toBe("/packs?all=1");
    expect(catalogHref(parseFilters({}))).toBe("/packs");
  });
});

describe("nearestVersions", () => {
  const versions = ["1.21.8", "1.21.7", "1.21.5", "1.21.4", "1.21.3", "1.21.1", "1.20.1"];

  it("goes outwards from the target, the newer one first on a tie", () => {
    expect(nearestVersions("1.21.4", versions, 4)).toEqual([
      "1.21.5",
      "1.21.3",
      "1.21.7",
      "1.21.1",
    ]);
  });

  it("knows nothing about an unsupported version", () => {
    expect(nearestVersions("1.8.9", versions)).toEqual([]);
  });
});
