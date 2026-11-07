import type { components } from "@/lib/api/schema";

import { sourcesCopy } from "./copy";

export type RunSummary = components["schemas"]["RunSummary"];

const TIME_ZONE = "Europe/Kyiv";
const COUNTERS = ["created", "updated", "unchanged", "skipped", "failed"] as const;

/** «7 листопада, 21:05» in Kyiv time. */
export function formatWhen(iso: string): string {
  return new Date(iso).toLocaleString("uk-UA", {
    day: "numeric",
    month: "long",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: TIME_ZONE,
  });
}

/** «918 нових · 4 оновлено»: only the counters that are not zero. */
export function formatCounts(run: RunSummary): string {
  return COUNTERS.filter((name) => run[name] > 0)
    .map((name) => `${run[name].toLocaleString("uk-UA")} ${sourcesCopy.counts[name]}`)
    .join(" · ");
}
