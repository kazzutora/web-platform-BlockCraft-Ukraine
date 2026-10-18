import { describe, expect, it } from "vitest";

import { hitHref, hitMeta } from "./hits";
import type { SearchHit } from "./types";

const base: SearchHit = {
  kind: "mod",
  id: "sodium",
  title: "Sodium",
  summary: "",
  image: null,
  project_type: "mod",
  latest_game_version: "26.3",
  loaders: ["fabric", "quilt", "babric"],
  author: null,
  modes: [],
  color_bucket: null,
  address: null,
  items_count: null,
};

describe("search hits", () => {
  it("link to the page of their kind", () => {
    expect(hitHref(base)).toBe("/mods/sodium");
    expect(hitHref({ kind: "skin", id: "7" })).toBe("/skins/7");
    expect(hitHref({ kind: "server", id: "sich" })).toBe("/servers/sich");
    expect(hitHref({ kind: "collection", id: "3" })).toBe("/c/3");
  });

  it("describe themselves in one line", () => {
    expect(hitMeta(base)).toBe("Мод · 26.3 · Fabric, Quilt");
    expect(hitMeta({ ...base, kind: "skin", author: "Mavka" })).toBe("Скін · Mavka");
    expect(
      hitMeta({ ...base, kind: "server", address: "play.sich.ua", modes: ["survival", "rp"] }),
    ).toBe("play.sich.ua · Виживання, Рольова гра");
    expect(hitMeta({ ...base, kind: "collection", items_count: 3 })).toBe("Колекція · 3 елементи");
  });
});
