import { describe, expect, it } from "vitest";

import { chartGeometry } from "./chart";

const at = (minutes: number) => new Date(Date.UTC(2026, 9, 18, 12, minutes)).toISOString();

describe("chartGeometry", () => {
  it("draws one line across the range with the maximum near the top", () => {
    const { line, ticks } = chartGeometry(
      [
        { ts: at(0), players: 0, is_online: true },
        { ts: at(5), players: 10, is_online: true },
        { ts: at(10), players: 5, is_online: true },
      ],
      100,
      50,
    );

    expect(line.startsWith("M0.0,50.0")).toBe(true);
    expect(line.match(/[ML]/g)).toEqual(["M", "L", "L"]);
    expect(line).toContain("L100.0,");
    expect(ticks.map((tick) => tick.value)).toEqual([0, 6, 11]);
  });

  it("breaks the line where the server was offline", () => {
    const { line, area } = chartGeometry(
      [
        { ts: at(0), players: 3, is_online: true },
        { ts: at(5), players: 0, is_online: false },
        { ts: at(10), players: 4, is_online: true },
      ],
      100,
      50,
    );

    expect(line.match(/M/g)).toHaveLength(2);
    expect(area.match(/Z/g)).toHaveLength(2);
  });
});
