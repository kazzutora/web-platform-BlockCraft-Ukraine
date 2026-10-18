import { describe, expect, it } from "vitest";

import { versionDescending } from "@/lib/versions";

import { formatCount, formatFileSize, loaderName, mainLoadersOf } from "./format";

describe("format", () => {
  it("shortens big counts the Ukrainian way", () => {
    expect(formatCount(248_165_612)).toMatch(/^248,2\s?млн$/);
    expect(formatCount(950)).toBe("950");
  });

  it("formats file sizes", () => {
    expect(formatFileSize(512)).toBe("512 Б");
    expect(formatFileSize(1_572_864)).toBe("1,5 МБ");
  });

  it("names loaders and keeps only the main ones", () => {
    expect(loaderName("neoforge")).toBe("NeoForge");
    expect(mainLoadersOf(["babric", "fabric", "datapack", "quilt"])).toEqual(["fabric", "quilt"]);
  });
});

describe("versionDescending", () => {
  it("sorts both version schemes numerically", () => {
    expect(["1.21.4", "26.1", "1.21.11", "1.8.9", "26.3"].sort(versionDescending)).toEqual([
      "26.3",
      "26.1",
      "1.21.11",
      "1.21.4",
      "1.8.9",
    ]);
  });
});
