import { describe, expect, it } from "vitest";

import { catalogHref, parseFilters, toApiQuery, toggleMode } from "./filters";

describe("server filters", () => {
  it("keeps only known values from the URL", () => {
    expect(parseFilters({ mode: "pvp,unknown,rp", edition: "pc", online: "1", page: "x" })).toEqual(
      {
        modes: ["pvp", "rp"],
        edition: "",
        language: "",
        online: true,
        whitelist: false,
        sort: "",
        q: "",
        page: 1,
      },
    );
  });

  it("sends booleans and lists to the API", () => {
    expect(toApiQuery(parseFilters({ mode: "survival,smp", online: "1", sort: "online" }))).toEqual(
      { page: 1, mode: "survival,smp", online: true, sort: "online" },
    );
  });

  it("links toggle filters and reset the page", () => {
    const filters = parseFilters({ online: "1", page: "4" });

    expect(catalogHref(filters, { modes: toggleMode(filters.modes, "pvp") })).toBe(
      "/servers?mode=pvp&online=1",
    );
    expect(catalogHref(filters, { online: false })).toBe("/servers");
  });
});
