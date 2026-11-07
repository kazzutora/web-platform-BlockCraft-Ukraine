import { getServerClient } from "@/lib/api/server-client";
import type { components } from "@/lib/api/schema";

import { sourcesCopy as copy } from "./copy";
import { type RunSummary, formatCounts, formatWhen } from "./format";

type Source = components["schemas"]["Source"];

/** The registry with the latest runs; null when the API fails (the page shows why). */
async function getSources(): Promise<Source[] | null> {
  try {
    const client = await getServerClient();
    const { data, response } = await client.GET("/api/v1/sources");
    if (!data) throw new Error(`GET /api/v1/sources failed: ${response.status}`);
    return data;
  } catch (error) {
    console.error(error);
    return null;
  }
}

const statusTone: Record<RunSummary["status"], string> = {
  ok: "bg-accent",
  running: "border border-muted",
  partial: "bg-muted",
  failed: "bg-danger",
};

function RunLine({ run }: { run: RunSummary }) {
  const counts = formatCounts(run);
  return (
    <span className="inline-flex flex-wrap items-center gap-x-2 gap-y-1 tabular-nums">
      <span aria-hidden className={`size-2 shrink-0 ${statusTone[run.status]}`} />
      <span>
        {run.status === "running" ? copy.running : formatWhen(run.finished_at ?? run.started_at)}
        {" · "}
        {copy.status[run.status]}
      </span>
      {counts && <span className="text-muted">{counts}</span>}
    </span>
  );
}

/** /sources: every source from the registry with its terms and latest sync. */
export async function SourcesList() {
  const sources = await getSources();
  if (!sources) return <p className="text-muted">{copy.error}</p>;
  return (
    <ul className="flex flex-col">
      {sources.map((source) => (
        <li key={source.key} className="flex flex-col gap-4 border-t border-line py-10">
          <div className="flex flex-col gap-2">
            <h2 className="text-h2">{source.name}</h2>
            <p className="max-w-prose">{source.description}</p>
            <p className="flex flex-wrap gap-x-6 gap-y-1 text-sm">
              <a
                href={source.url}
                target="_blank"
                rel="noopener"
                className="underline underline-offset-4"
              >
                {copy.site} ↗
              </a>
              {source.terms_url && (
                <a
                  href={source.terms_url}
                  target="_blank"
                  rel="noopener"
                  className="underline underline-offset-4"
                >
                  {copy.terms} ↗
                </a>
              )}
            </p>
          </div>
          {source.jobs.length === 0 ? (
            <p className="text-meta text-muted">{copy.onDemand}</p>
          ) : (
            <dl className="flex flex-col gap-3 text-meta">
              <dt className="caps text-muted">{copy.jobsLabel}</dt>
              {source.jobs.map((job) => (
                <dd key={job.key} className="flex flex-col gap-1 border-l border-line pl-3">
                  <span>{job.title}</span>
                  {job.last_run ? (
                    <RunLine run={job.last_run} />
                  ) : (
                    <span className="text-muted">{copy.never}</span>
                  )}
                </dd>
              ))}
            </dl>
          )}
        </li>
      ))}
    </ul>
  );
}
