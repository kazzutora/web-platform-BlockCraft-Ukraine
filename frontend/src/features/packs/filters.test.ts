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

  it("builds the API query and links back to the catalog", () => {
    const filters = parseFilters({ loader: "fabric", style: "tech", page: "3" });

    expect(toApiQuery(filters)).toEqual({ page: 3, loader: "fabric", style: "tech" });
    expect(catalogHref(filters, { styles: toggleStyle(filters.styles, "magic") })).toBe(
      "/packs?loader=fabric&style=tech%2Cmagic",
    );
    expect(catalogHref(filters, { loader: "", styles: [] })).toBe("/packs");
  });
});
