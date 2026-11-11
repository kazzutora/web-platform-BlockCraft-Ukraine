import { describe, expect, it } from "vitest";

import { catalogHref, effectiveLanguage, parseFilters, toApiQuery, toggle } from "./filters";

describe("server filters", () => {
  it("keeps only known values from the URL", () => {
    expect(
      parseFilters({ kind: "pc", country: "ua", category: "smp,BAD!,pvp", online: "1", page: "x" }),
    ).toEqual({
      language: null,
      country: "UA",
      kind: "",
      version: "",
      categories: ["smp", "pvp"],
      online: true,
      sort: "",
      q: "",
      page: 1,
    });
  });

  it("uses the catalog default language until the URL names one", () => {
    expect(effectiveLanguage(parseFilters({}), "uk")).toBe("uk");
    expect(effectiveLanguage(parseFilters({ language: "all" }), "uk")).toBe("");
    expect(effectiveLanguage(parseFilters({ language: "en" }), "uk")).toBe("en");
  });

  it("always sends the language to the API", () => {
    expect(toApiQuery(parseFilters({ kind: "modded", online: "1", sort: "online" }), "uk")).toEqual(
      { page: 1, language: "uk", kind: "modded", online: true, sort: "online" },
    );
    expect(toApiQuery(parseFilters({ language: "all" }), "uk")).toEqual({ page: 1, language: "" });
  });

  it("links toggle filters and reset the page", () => {
    const filters = parseFilters({ online: "1", page: "4" });

    expect(catalogHref(filters, { categories: toggle(filters.categories, "pvp") })).toBe(
      "/servers?category=pvp&online=1",
    );
    expect(catalogHref(filters, { online: false })).toBe("/servers");
    expect(catalogHref(filters, { language: "all", online: false })).toBe("/servers?language=all");
  });
});
