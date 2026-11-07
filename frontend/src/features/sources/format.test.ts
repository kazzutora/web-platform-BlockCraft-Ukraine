import { describe, expect, it } from "vitest";

import { formatCounts, formatWhen } from "./format";

const run = {
  status: "ok" as const,
  started_at: "2026-11-07T19:05:00Z",
  finished_at: "2026-11-07T19:06:00Z",
  created: 918,
  updated: 4,
  unchanged: 0,
  skipped: 0,
  failed: 0,
};

describe("sources format", () => {
  it("shows only the counters that changed", () => {
    expect(formatCounts(run)).toBe("918 нових · 4 оновлено");
    // Ukrainian groups thousands with a no-break space
    expect(formatCounts({ ...run, created: 0, updated: 0, unchanged: 1200 })).toBe(
      "1 200 без змін",
    );
  });

  it("shows the time in Kyiv", () => {
    expect(formatWhen(run.started_at)).toBe("7 листопада о 21:05");
  });
});
