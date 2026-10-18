"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { ChoiceChips } from "@/components/ui/ChoiceChips";
import { Skeleton } from "@/components/ui/Skeleton";
import { api } from "@/lib/api/client";
import { queryKeys } from "@/lib/query-keys";

import { chartGeometry } from "./chart";
import { serversCopy } from "./copy";
import type { Stats, StatsRange } from "./types";

const copy = serversCopy.stats;
const WIDTH = 600;
const HEIGHT = 200;

// A fixed zone: the server render (UTC container) and the browser must print the same text
const TIME_ZONE = "Europe/Kyiv";

function axisLabel(iso: string, range: StatsRange): string {
  const date = new Date(iso);
  return range === "24h"
    ? date.toLocaleTimeString("uk-UA", { hour: "2-digit", minute: "2-digit", timeZone: TIME_ZONE })
    : date.toLocaleDateString("uk-UA", { day: "numeric", month: "short", timeZone: TIME_ZONE });
}

/** Players online for 24 hours (every ping) or 7 days (hourly averages), uptime and peak. */
export function OnlineChart({ slug, initial }: { slug: string; initial: Stats | null }) {
  const [range, setRange] = useState<StatsRange>("24h");
  const stats = useQuery({
    queryKey: queryKeys.servers.stats(slug, range),
    initialData: range === "24h" && initial ? initial : undefined,
    queryFn: async () => {
      const { data } = await api.GET("/api/v1/servers/{slug}/stats", {
        params: { path: { slug }, query: { range } },
      });
      if (!data) throw new Error("GET stats failed");
      return data;
    },
  });
  const rangeLabel = copy.ranges.find((item) => item.value === range)?.label ?? range;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <ChoiceChips
          label={rangeLabel}
          hideLabel
          options={copy.ranges as { value: StatsRange; label: string }[]}
          value={range}
          onChange={setRange}
        />
        {stats.data && stats.data.points.length > 0 && (
          <p className="text-meta text-muted tabular-nums">
            {[
              stats.data.uptime_percent !== null ? copy.uptime(stats.data.uptime_percent) : "",
              copy.peak(stats.data.peak_players),
            ]
              .filter(Boolean)
              .join(" · ")}
          </p>
        )}
      </div>

      {stats.isPending ? (
        <Skeleton className="h-52 w-full" />
      ) : !stats.data?.points.length ? (
        <p className="border border-line p-6 text-muted">{copy.empty}</p>
      ) : (
        <Chart stats={stats.data} range={range} rangeLabel={rangeLabel} />
      )}
    </div>
  );
}

function Chart({
  stats,
  range,
  rangeLabel,
}: {
  stats: Stats;
  range: StatsRange;
  rangeLabel: string;
}) {
  const { line, area, ticks } = chartGeometry(stats.points, WIDTH, HEIGHT);
  const uptime =
    stats.uptime_percent !== null ? copy.uptime(stats.uptime_percent).toLowerCase() : copy.noUptime;
  const first = stats.points[0];
  const last = stats.points[stats.points.length - 1];

  return (
    <figure className="flex flex-col gap-2">
      <div className="relative mt-3 h-52 border-b border-l border-line">
        {ticks.slice(1).map((tick) => (
          <div
            key={tick.value}
            aria-hidden
            className="absolute inset-x-0 border-t border-dashed border-line"
            style={{ top: `${(tick.y / HEIGHT) * 100}%` }}
          >
            <span className="absolute -top-2.5 left-1 bg-bg px-1 text-meta text-muted tabular-nums">
              {tick.value}
            </span>
          </div>
        ))}
        <svg
          role="img"
          aria-label={copy.chartLabel(rangeLabel, stats.peak_players, uptime)}
          viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
          preserveAspectRatio="none"
          className="absolute inset-0 size-full overflow-visible"
        >
          <path d={area} className="fill-accent/15" />
          <path
            d={line}
            className="fill-none stroke-accent"
            strokeWidth={2}
            vectorEffect="non-scaling-stroke"
          />
        </svg>
      </div>
      <figcaption className="flex justify-between text-meta text-muted tabular-nums" aria-hidden>
        <span>{axisLabel(first.ts, range)}</span>
        <span>{axisLabel(last.ts, range)}</span>
      </figcaption>
    </figure>
  );
}
