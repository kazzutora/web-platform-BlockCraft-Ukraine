import { describe, expect, it } from "vitest";

import { catalogHref, parseFilters, toApiQuery, toggleStyle } from "./filters";

describe("pack filters", () => {
  it("keeps only known values from the URL", () => {
    const filters = parseFilters({
      version: "1.21.1",
      loader: "rift",
      style: "tech,unknown,magic",
      official: "1",
      sort: "random",
      page: "-3",
    });

    expect(filters).toEqual({
      gameVersion: "1.21.1",
      loader: "",
      styles: ["tech", "magic"],
      official: true,
      sort: "",
      q: "",
      page: 1,
    });
  });

  it("takes any release number from the URL and leaves the check to the API", () => {
    expect(parseFilters({ version: "26.3" }).gameVersion).toBe("26.3");
    expect(parseFilters({ version: "1.8.9" }).gameVersion).toBe("1.8.9");
    expect(parseFilters({ version: "26.4-snapshot-7" }).gameVersion).toBe("");
    expect(parseFilters({ version: "<script>" }).gameVersion).toBe("");
  });

  it("builds the API query and links back to the catalog", () => {
    const filters = parseFilters({ loader: "fabric", style: "tech", page: "3" });

    expect(toApiQuery(filters)).toEqual({ page: 3, loader: "fabric", style: "tech" });
    expect(catalogHref(filters, { styles: toggleStyle(filters.styles, "magic") })).toBe(
      "/packs?loader=fabric&style=tech%2Cmagic",
    );
    expect(catalogHref(filters, { loader: "", styles: [] })).toBe("/packs");
  });
});
