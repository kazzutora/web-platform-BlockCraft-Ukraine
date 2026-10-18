import { describe, expect, it } from "vitest";

import { catalogHref, parseFilters, toApiQuery } from "./filters";

describe("skin filters", () => {
  it("keeps only known values from the URL", () => {
    const filters = parseFilters({
      color: "blue",
      model: "slim",
      style: "anime,unknown,ukrainian",
      sort: "weird",
      page: "2",
    });

    expect(filters).toEqual({
      color: "blue",
      model: "slim",
      styles: ["anime", "ukrainian"],
      sort: "",
      q: "",
      page: 2,
    });
  });

  it("ignores an unknown colour and model", () => {
    const filters = parseFilters({ color: "magenta", model: "wide" });

    expect([filters.color, filters.model]).toEqual(["", ""]);
  });

  it("builds the API query without empty filters", () => {
    expect(toApiQuery(parseFilters({ style: "cute,mob", sort: "new" }))).toEqual({
      page: 1,
      style: "cute,mob",
      sort: "new",
    });
  });

  it("links reset the page", () => {
    const filters = parseFilters({ color: "red", page: "3" });

    expect(catalogHref(filters, { model: "classic" })).toBe("/skins?color=red&model=classic");
    expect(catalogHref(filters, { color: "" })).toBe("/skins");
  });
});
