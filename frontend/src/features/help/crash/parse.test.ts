import { readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

import { clip, modsOf, outsideRange, parseCrashLog, problemsOf, readableRange } from "./parse";

/** Real logs from public GitHub issues (the first line of each file names it). */
function fixture(name: string) {
  return parseCrashLog(readFileSync(join(__dirname, "fixtures", name), "utf8"));
}

describe("parseCrashLog on real logs", () => {
  it("Fabric: a missing dependency, with the game and the loader", () => {
    const report = fixture("fabric-missing-dependency.log");

    expect(report).toMatchObject({
      loader: "fabric",
      loaderVersion: "0.19.5",
      gameVersion: "26.1.2",
    });
    expect(report.findings).toEqual([
      {
        type: "missing",
        mod: { id: "emf_compat_takeaseat", name: "EMF Compat: Take a Seat", version: "1.0.0" },
        needs: { id: "seatify" },
        range: "",
      },
    ]);
  });

  it("Fabric: Fabric API under its old id", () => {
    const report = fixture("fabric-missing-fabric-api.log");

    expect(report.findings).toEqual([
      expect.objectContaining({ type: "missing", needs: { id: "fabric" } }),
    ]);
    expect(modsOf(report)).toEqual([
      { id: "a_good_place", name: "A Good Place" },
      { id: "fabric", name: undefined },
    ]);
  });

  it("Fabric: two mods that refuse each other", () => {
    expect(fixture("fabric-incompatible-mods.log").findings).toEqual([
      {
        type: "incompatible",
        mod: { id: "sodium", name: "Sodium", version: "0.8.14+mc1.21.11" },
        other: { id: "iris", name: "Iris", version: "1.10.7+mc1.21.11" },
      },
    ]);
  });

  it("Fabric: a long unmet dependency listing", () => {
    const report = fixture("fabric-unmet-dependencies.log");
    const missing = report.findings.filter((finding) => finding.type === "missing");

    // 16 lines, one of them «can't be loaded due to other constraints» — not a missing mod
    expect(missing).toHaveLength(15);
    expect(missing).toContainEqual({
      type: "missing",
      mod: { id: "xaerominimap", name: "Xaero's Minimap", version: "21.22.3.1" },
      needs: { id: "fabric" },
      range: "0.43.1 or later",
    });
    expect(missing).toContainEqual(
      expect.objectContaining({ needs: { id: "fabric-command-api-v1" } }),
    );
  });

  it("Fabric: a mod for another Minecraft", () => {
    const report = fixture("fabric-wrong-minecraft.log");

    expect(report.gameVersion).toBe("1.21.1");
    expect(report.findings).toEqual([
      {
        type: "wrong_game",
        mod: { id: "swe", name: "Spaceward Expansion", version: "1.2.3" },
        expected: "1.21",
        actual: "1.21.1",
      },
    ]);
  });

  it("NeoForge: a mod for another Minecraft", () => {
    const report = fixture("neoforge-wrong-minecraft.log");

    expect(report).toMatchObject({ loader: "neoforge", gameVersion: "1.21" });
    expect(report.findings).toEqual([
      {
        type: "wrong_game",
        mod: { id: "touhou_little_maid" },
        expected: "[1.21.1,1.21.2)",
        actual: "1.21",
      },
    ]);
  });

  it("NeoForge: the loader is newer than the mod allows", () => {
    const report = fixture("neoforge-loader-too-old.log");

    expect(report).toMatchObject({ loader: "neoforge", loaderVersion: "21.1.230" });
    expect(report.findings).toEqual([
      {
        type: "wrong_loader",
        mod: { id: "sepals" },
        loader: "neoforge",
        expected: "[21.1.132,21.1.132]",
        actual: "21.1.230",
      },
    ]);
  });

  it("NeoForge: an optional dependency of the wrong version", () => {
    expect(fixture("neoforge-optional-dependency.log").findings).toEqual([
      {
        type: "wrong_dependency",
        mod: { id: "logisticsnetworks" },
        needs: { id: "buildinggadgets2" },
        expected: "[1.3.8,1.4)",
        actual: "21.1.1",
        optional: true,
      },
    ]);
  });

  it("Forge: the same mod in two files", () => {
    expect(fixture("forge-duplicate-mods.log").findings).toEqual([
      {
        type: "duplicate",
        id: "rubidium",
        files: ["xenon-1.20.1-0.3.1.jar", "embeddium-0.3.30+mc1.20.1.jar"],
      },
    ]);
  });

  it("Java: class file 63 needs Java 19, the runtime is Java 17", () => {
    expect(fixture("java-too-old.log").findings).toEqual([
      { type: "java", required: 19, current: 17 },
    ]);
  });
});

describe("parseCrashLog on anything else", () => {
  it("shows the first exception when no known problem is found", () => {
    const report = parseCrashLog(
      '[12:00:00] [main/INFO]: hello\njava.lang.NullPointerException: Cannot invoke "x"\n\tat a.b(C.java:1)',
    );

    expect(report.findings).toEqual([]);
    expect(report.firstError).toBe('java.lang.NullPointerException: Cannot invoke "x"');
  });

  it("finds nothing in an empty paste", () => {
    expect(parseCrashLog("")).toEqual({
      loader: "",
      loaderVersion: "",
      gameVersion: "",
      findings: [],
      firstError: "",
    });
  });
});

describe("readableRange", () => {
  it("reads Maven ranges", () => {
    expect(readableRange("[1.21.1,1.21.2)")).toBe("від 1.21.1 до 1.21.2");
    expect(readableRange("[21.1.132,21.1.132]")).toBe("21.1.132");
    expect(readableRange("[9,)")).toBe("9 або новіша");
    expect(readableRange("0.43.1 or later")).toBe("0.43.1 або новіша");
  });
});

describe("problemsOf", () => {
  it("gives one row per missing mod with everyone who needs it", () => {
    const problems = problemsOf(fixture("fabric-unmet-dependencies.log"));

    expect(problems).toHaveLength(2);
    const [fabric, command] = problems;
    // «0.34.0 or later» … «0.43.1 or later»: the newest covers everyone
    expect(fabric).toMatchObject({
      type: "missing",
      needs: { id: "fabric" },
      range: "0.43.1 or later",
    });
    expect(fabric.type === "missing" && fabric.mods).toHaveLength(14);
    expect(command).toEqual({
      type: "missing",
      needs: { id: "fabric-command-api-v1" },
      mods: [{ id: "spark", name: "spark", version: "1.6.3" }],
      range: "",
    });
  });

  it("keeps a range everyone agrees on and the other problems as they are", () => {
    expect(problemsOf(fixture("fabric-incompatible-mods.log"))).toEqual(
      fixture("fabric-incompatible-mods.log").findings,
    );
    expect(problemsOf(fixture("fabric-missing-dependency.log"))[0]).toMatchObject({
      mods: [{ id: "emf_compat_takeaseat" }],
      range: "",
    });
  });
});

describe("Fabric ranges and big pastes", () => {
  it("reads «any version between … of Minecraft»", () => {
    const report = fixture("fabric-version-between.log");

    expect(report.findings).toEqual([
      expect.objectContaining({ type: "missing", needs: { id: "fabric" }, range: "" }),
      {
        type: "wrong_game",
        mod: { id: "netherwartblock", name: "Nether Wart Blocks to Nether Warts", version: "8" },
        expected: "between 1.21 (inclusive) and 1.22- (exclusive)",
        actual: "26.2",
      },
    ]);
    expect(readableRange("between 1.21 (inclusive) and 1.22- (exclusive)")).toBe(
      "від 1.21 до 1.22",
    );
  });

  it("stays fast on a huge log pasted without line breaks", () => {
    const real = readFileSync(join(__dirname, "fixtures", "fabric-unmet-dependencies.log"), "utf8");
    const oneLine = real.replace(/\n/g, " ").repeat(800); // ≈ 2 MB, one line

    const started = performance.now();
    const report = parseCrashLog(oneLine);

    expect(performance.now() - started).toBeLessThan(3000);
    expect(report.findings.some((finding) => finding.type === "missing")).toBe(true);
  });

  it("keeps the head (game, loader) and the tail (error) of a long log", () => {
    const head = "[main/INFO]: Loading Minecraft 1.21.1 with Fabric Loader 0.17.2\n";
    const clipped = clip(head + "x".repeat(3_000_000) + "\nTAIL");

    expect(clipped.startsWith(head)).toBe(true);
    expect(clipped.endsWith("TAIL")).toBe(true);
    expect(clipped.length).toBeLessThanOrEqual(2_000_001);
  });
});

describe("outsideRange", () => {
  it("tells newer from older", () => {
    expect(outsideRange("21.1.230", "[21.1.132,21.1.132]")).toBe("above");
    expect(outsideRange("21.0.167", "[21.1.0,)")).toBe("below");
    expect(outsideRange("1.21", "[1.21.1,1.21.2)")).toBe("below");
    expect(outsideRange("1.21.2", "[1.21.1,1.21.2)")).toBe("above");
    expect(outsideRange("1.21.1", "[1.21.1,1.21.2)")).toBeNull();
    expect(outsideRange("1.0", "0.43.1 or later")).toBeNull();
  });
});
