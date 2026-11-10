import { describe, expect, it } from "vitest";

import { reasonOf, sortItems } from "./items";
import type { PackItem } from "./types";

function item(slug: string, reason: PackItem["reason"], requiredBy: string[] = []): PackItem {
  return {
    project: { slug, title: slug.toUpperCase(), icon_url: "", project_type: "mod", summary: "" },
    version: null,
    reason,
    required_by: requiredBy,
    env_client: "required",
    env_server: "required",
  };
}

describe("pack items", () => {
  it("puts the author's picks first, engines next, libraries last", () => {
    const sorted = sortItems([
      item("api", "dependency"),
      item("iris", "implicit"),
      item("bsl", "requested"),
    ]);

    expect(sorted.map((entry) => entry.project.slug)).toEqual(["bsl", "iris", "api"]);
  });

  it("explains why a project is there", () => {
    const titles = new Map([["extra", "Sodium Extra"]]);

    expect(reasonOf(item("sodium", "dependency", ["extra"]), titles)).toBe(
      "потрібен для Sodium Extra",
    );
    expect(reasonOf(item("iris", "implicit", ["bsl"]), titles)).toBe("рушій шейдерів для bsl");
    expect(reasonOf(item("bsl", "requested"), titles)).toBe("");
  });
});
