/**
 * A Minecraft crash log → what went wrong, in the browser (R8.5). The log never leaves the
 * player's computer: only the mod ids found here are sent to `/help/crash`.
 *
 * Patterns come from real logs of Fabric Loader, NeoForge / Forge (ModSorter) and the JVM —
 * see ./fixtures, each with its public source. Matching goes line by line with bounded
 * patterns: a 2 MB paste (even one with lost line breaks) must not freeze the tab.
 */

export type ModRef = { id: string; name?: string; version?: string };

export type Finding =
  /** A required mod is not installed. `range` — "" for any version. */
  | { type: "missing"; mod: ModRef; needs: ModRef; range: string }
  /** Made for another Minecraft version. */
  | { type: "wrong_game"; mod: ModRef; expected: string; actual: string }
  /** Needs another loader build. */
  | { type: "wrong_loader"; mod: ModRef; loader: string; expected: string; actual: string }
  /** Needs another version of a mod that is installed. */
  | {
      type: "wrong_dependency";
      mod: ModRef;
      needs: ModRef;
      expected: string;
      actual: string;
      optional: boolean;
    }
  /** Two installed mods refuse to work together. */
  | { type: "incompatible"; mod: ModRef; other: ModRef }
  /** The same mod in several files. */
  | { type: "duplicate"; id: string; files: string[] }
  /** The game or a mod needs a newer Java. */
  | { type: "java"; required: number; current: number };

export type CrashLoader = "fabric" | "quilt" | "forge" | "neoforge" | "";

export type CrashReport = {
  loader: CrashLoader;
  loaderVersion: string;
  gameVersion: string;
  findings: Finding[];
  /** The first exception line, for logs with no known problem. */
  firstError: string;
};

/** The start of a log names the game and the loader; the error is near its end. */
export const LOG_HEAD = 64 * 1024;
export const MAX_LOG = 2_000_000;
/** Longer lines are cut into pieces at the markers below, then cut short */
const MAX_LINE = 4096;

const LOADER_IDS: Record<string, CrashLoader> = {
  fabricloader: "fabric",
  quilt_loader: "quilt",
  forge: "forge",
  neoforge: "neoforge",
};

// Fabric Loader: «Mod 'Xaero's Minimap' (xaerominimap) 21.22.3.1 requires …»
// A name may hold an apostrophe, but never «' (» — that is where the id starts
const NAME = String.raw`((?:[^'\n]|'(?! \())+?)`;
const ID = String.raw`([\w.\-]+)`;
const MOD = String.raw`Mod '${NAME}' \(${ID}\) (\S+)`;
// «any version», «version 0.43.1 or later», «any version between 1.21 (inclusive) and …»
const WANTS = String.raw`requires ((?:any )?version[^,\n]*?) of`;
const DEPENDENCY = String.raw`(?:mod '${NAME}' \(${ID}\)|'${NAME}' \(${ID}\)|${ID})`;
const FABRIC_MISSING = new RegExp(`${MOD} ${WANTS} ${DEPENDENCY}, which is missing!`);
const FABRIC_WRONG = new RegExp(
  String.raw`${MOD} ${WANTS} (?:mod )?'${NAME}' \(${ID}\), but only the wrong version is present: ([^!\s]+)!`,
);
const FABRIC_INCOMPATIBLE = new RegExp(
  String.raw`${MOD} is incompatible with [^,\n]*? of mod '${NAME}' \(${ID}\), yet a conflicting version is present: ([^!\s]+)!`,
);
const FABRIC_LOADING = /Loading Minecraft (\S+) with (Fabric|Quilt) Loader (\S+)/;

// NeoForge / Forge ModSorter
const SORTER_HEADER =
  /(Missing or unsupported mandatory dependencies|Unsupported installed optional dependencies):/;
const SORTER_LINE =
  /Mod ID: '([^']+)', Requested by: '([^']+)', Expected range: '([^']+)', Actual version: '([^']+)'/;
const DUPLICATE = /Mod ID: '([^']+)' from mod files: (.+)/;

// The JVM: class file version 65 is Java 21 (version − 44)
const JAVA =
  /class file version (\d+)(?:\.\d+)?\), this version of the Java Runtime only recognizes class file versions up to (\d+)/;

const FIRST_ERROR = /^\s*(Caused by: .+|[\w.$]{1,200}(?:Exception|Error)(?::.*)?)$/;

/** A paste or a file, cut to what the parser needs: the head and the tail of the log. */
export function clip(text: string): string {
  if (text.length <= MAX_LOG) return text;
  return `${text.slice(0, LOG_HEAD)}\n${text.slice(-(MAX_LOG - LOG_HEAD))}`;
}

/** Lines of the log; a huge line (lost line breaks) is split at Fabric / ModSorter items. */
function linesOf(log: string): string[] {
  const lines: string[] = [];
  for (const line of log.split("\n")) {
    if (line.length <= MAX_LINE) {
      lines.push(line);
      continue;
    }
    for (const piece of line.split(/(?= - Mod '|\tMod ID: '| Mod ID: ')/)) {
      lines.push(piece.slice(0, MAX_LINE));
    }
  }
  return lines;
}

/** Fabric's «any version» → "", «version 0.43.1 or later» → «0.43.1 or later». */
function fabricRange(wants: string): string {
  return wants.replace(/^any version\s*/, "").replace(/^version\s*/, "");
}

function dependency(match: RegExpMatchArray, from: number): ModRef {
  const [modName, modId, quotedName, quotedId, bare] = match.slice(from, from + 5);
  if (modId) return { id: modId, name: modName };
  if (quotedId) return { id: quotedId, name: quotedName };
  return { id: bare };
}

export function parseCrashLog(text: string): CrashReport {
  const lines = linesOf(clip(text).replace(/\r\n/g, "\n"));
  const findings: Finding[] = [];
  let loader: CrashLoader = "";
  let loaderVersion = "";
  let gameVersion = "";
  let optional = false;
  let firstError = "";
  let sawFabric = false;

  const wrong = (mod: ModRef, needs: ModRef, expected: string, actual: string, opt: boolean) => {
    if (needs.id === "minecraft") {
      findings.push({ type: "wrong_game", mod, expected, actual });
      gameVersion ||= actual;
    } else if (LOADER_IDS[needs.id]) {
      findings.push({ type: "wrong_loader", mod, loader: LOADER_IDS[needs.id], expected, actual });
      loader ||= LOADER_IDS[needs.id];
      if (LOADER_IDS[needs.id] === loader && actual !== "[MISSING]") loaderVersion ||= actual;
    } else if (needs.id !== "java") {
      // Java is said better by the JVM line below
      findings.push({ type: "wrong_dependency", mod, needs, expected, actual, optional: opt });
    }
  };

  for (const line of lines) {
    if (!sawFabric && line.includes("net.fabricmc.loader")) sawFabric = true;

    const loading = line.match(FABRIC_LOADING);
    if (loading && !gameVersion) {
      gameVersion = loading[1];
      loader = loading[2] === "Quilt" ? "quilt" : "fabric";
      loaderVersion = loading[3];
      continue;
    }

    let match = line.match(FABRIC_MISSING);
    if (match) {
      findings.push({
        type: "missing",
        mod: { id: match[2], name: match[1], version: match[3] },
        needs: dependency(match, 5),
        range: fabricRange(match[4]),
      });
      continue;
    }

    match = line.match(FABRIC_WRONG);
    if (match) {
      wrong(
        { id: match[2], name: match[1], version: match[3] },
        { id: match[6], name: match[5] },
        fabricRange(match[4]),
        match[7],
        false,
      );
      continue;
    }

    match = line.match(FABRIC_INCOMPATIBLE);
    if (match) {
      findings.push({
        type: "incompatible",
        mod: { id: match[2], name: match[1], version: match[3] },
        other: { id: match[5], name: match[4], version: match[6] },
      });
      continue;
    }

    match = line.match(SORTER_HEADER);
    if (match) optional = match[1].startsWith("Unsupported installed optional");

    match = line.match(SORTER_LINE);
    if (match) {
      const [, needsId, modId, expected, actual] = match;
      if (actual === "[MISSING]" && !LOADER_IDS[needsId] && needsId !== "minecraft") {
        findings.push({
          type: "missing",
          mod: { id: modId },
          needs: { id: needsId },
          range: expected,
        });
      } else {
        wrong({ id: modId }, { id: needsId }, expected, actual, optional);
      }
      continue;
    }

    match = line.match(DUPLICATE);
    if (match) {
      const files = match[2]
        .split(",")
        .map((file) => file.trim())
        .filter(Boolean);
      findings.push({ type: "duplicate", id: match[1], files });
      continue;
    }

    match = line.match(JAVA);
    if (match) {
      findings.push({
        type: "java",
        required: Number(match[1]) - 44,
        current: Number(match[2]) - 44,
      });
      continue;
    }

    if (!firstError) firstError = line.match(FIRST_ERROR)?.[1].trim().slice(0, 300) ?? "";
  }

  if (!loader) {
    const all = lines.join("\n");
    if (sawFabric) loader = "fabric";
    else if (all.includes("net.neoforged")) loader = "neoforge";
    else if (all.includes("net.minecraftforge")) loader = "forge";
  }

  const found = unique(findings);
  return {
    loader,
    loaderVersion,
    gameVersion,
    findings: found,
    firstError: found.length ? "" : firstError,
  };
}

function unique(findings: Finding[]): Finding[] {
  const seen = new Set<string>();
  return findings.filter((finding) => {
    const key = JSON.stringify(finding);
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

/** Every mod the findings name, for `/help/crash` (ids and names only). */
export function modsOf(report: CrashReport): ModRef[] {
  const mods = new Map<string, ModRef>();
  const add = (mod: ModRef) => {
    if (!mods.has(mod.id) || (mod.name && !mods.get(mod.id)?.name)) mods.set(mod.id, mod);
  };
  for (const finding of report.findings) {
    if (finding.type === "duplicate") add({ id: finding.id });
    if ("mod" in finding) add(finding.mod);
    if ("needs" in finding) add(finding.needs);
    if ("other" in finding) add(finding.other);
  }
  return [...mods.values()].map(({ id, name }) => ({ id, name }));
}

/**
 * «[1.21.1,1.21.2)» → «від 1.21.1 до 1.21.2»; Fabric's «between 1.21 (inclusive) and
 * 1.22- (exclusive)» → «від 1.21 до 1.22»; «0.43.1 or later» → «0.43.1 або новіша».
 */
export function readableRange(range: string): string {
  const between = range.match(/^between (\S+?)-? \(inclusive\) and (\S+?)-? \((?:in|ex)clusive\)$/);
  if (between) return `від ${between[1]} до ${between[2]}`;
  const match = range.match(/^([[(])\s*([^,\])]*)\s*(?:,\s*([^\])]*))?\s*([\])])$/);
  if (!match) {
    return range.replace(/ or later$/, " або новіша").replace(/ or earlier$/, " або старіша");
  }
  const [, , from, to, close] = match;
  if (to === undefined) return from;
  if (from && from === to) return from;
  if (from && !to) return `${from} або новіша`;
  if (!from && to) return close === "]" ? `до ${to} включно` : `до ${to}`;
  return `від ${from} до ${to}`;
}

/** 1 when a is newer, -1 when older, 0 when equal (numbers by parts: 21.1.230 > 21.1.132). */
export function compareVersions(a: string, b: string): number {
  const parts = (version: string) =>
    version.split(/[.\-+]/).map((part) => Number.parseInt(part, 10));
  const [left, right] = [parts(a), parts(b)];
  for (let index = 0; index < Math.max(left.length, right.length); index += 1) {
    const [x, y] = [left[index] ?? 0, right[index] ?? 0];
    if (Number.isNaN(x) || Number.isNaN(y)) return 0;
    if (x !== y) return x > y ? 1 : -1;
  }
  return 0;
}

/** Whether `actual` is above or below a Maven range («[21.1.132,21.1.132]»), or unknown. */
export function outsideRange(actual: string, range: string): "above" | "below" | null {
  const match = range.match(/^([[(])\s*([^,\])]*)\s*(?:,\s*([^\])]*))?\s*([\])])$/);
  if (!match) return null;
  const [, open, from, rawTo, close] = match;
  const to = rawTo === undefined ? from : rawTo;
  if (from) {
    const versus = compareVersions(actual, from);
    if (versus < 0 || (versus === 0 && open === "(")) return "below";
  }
  if (to) {
    const versus = compareVersions(actual, to);
    if (versus > 0 || (versus === 0 && close === ")")) return "above";
  }
  return null;
}

/** What the page shows: one row per missing mod, with every mod that needs it. */
export type Problem =
  | Exclude<Finding, { type: "missing" }>
  | { type: "missing"; needs: ModRef; mods: ModRef[]; range: string };

/** «0.36.0 or later», «0.43.1 or later» → the newest one covers all; otherwise one shared. */
function strictest(ranges: Set<string>): string {
  const named = [...ranges].filter(Boolean);
  if (named.length === 1) return named[0];
  if (!named.length || !named.every((range) => range.endsWith(" or later"))) return "";
  return named.reduce((best, range) =>
    compareVersions(range.replace(" or later", ""), best.replace(" or later", "")) > 0
      ? range
      : best,
  );
}

export function problemsOf(report: CrashReport): Problem[] {
  const problems: Problem[] = [];
  const missing = new Map<string, { mods: ModRef[]; ranges: Set<string> }>();
  for (const finding of report.findings) {
    if (finding.type !== "missing") {
      problems.push(finding);
      continue;
    }
    let group = missing.get(finding.needs.id);
    if (!group) {
      group = { mods: [], ranges: new Set() };
      missing.set(finding.needs.id, group);
      // Keeps the place of the first mention among the other problems
      problems.push({ type: "missing", needs: finding.needs, mods: group.mods, range: "" });
    }
    group.mods.push(finding.mod);
    group.ranges.add(finding.range);
  }
  return problems.map((problem) =>
    problem.type === "missing"
      ? { ...problem, range: strictest(missing.get(problem.needs.id)?.ranges ?? new Set()) }
      : problem,
  );
}
