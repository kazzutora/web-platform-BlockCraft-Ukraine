"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { type FormEvent, useEffect, useState } from "react";

import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { useRequireAuth } from "@/features/auth/useRequireAuth";
import { api } from "@/lib/api/client";
import { type ApiError, fieldErrors } from "@/lib/api/errors";
import { queryKeys } from "@/lib/query-keys";

import { modsCopy } from "./copy";
import type { ImportJob } from "./types";

const copy = modsCopy.import;
const POLL_MS = 1500;
/** The import takes seconds; after this the page stops waiting and says so. */
const GIVE_UP_MS = 60_000;

type Started = { jobId: string | null; slug: string; title: string };

function errorText(code: string | undefined): string {
  return (code && copy.errors[code]) || copy.errors.failed;
}

/** «Не знайшли? Додайте з Modrinth»: a link → background import → a link to the new page. */
export function ImportFromModrinth() {
  const requireAuth = useRequireAuth();
  const [url, setUrl] = useState("");
  const [started, setStarted] = useState<Started | null>(null);

  const start = useMutation({
    mutationFn: async (value: string): Promise<Started> => {
      const { data, error } = await api.POST("/api/v1/mods/import", { body: { url: value } });
      if (error) throw error;
      return { jobId: data.job_id ?? null, slug: data.slug, title: data.title };
    },
    onSuccess: setStarted,
  });

  const jobId = started?.jobId ?? "";
  const [timedOutJob, setTimedOutJob] = useState("");
  const timedOut = Boolean(jobId) && timedOutJob === jobId;
  useEffect(() => {
    if (!jobId) return;
    const timer = setTimeout(() => setTimedOutJob(jobId), GIVE_UP_MS);
    return () => clearTimeout(timer);
  }, [jobId]);

  const job = useQuery({
    queryKey: queryKeys.mods.importJob(jobId),
    enabled: Boolean(jobId),
    queryFn: async (): Promise<ImportJob> => {
      const { data } = await api.GET("/api/v1/jobs/{job_id}", {
        params: { path: { job_id: jobId } },
      });
      if (!data) throw new Error("jobs");
      return data;
    },
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === "done" || status === "failed") return false;
      return timedOut ? false : POLL_MS;
    },
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    const value = url.trim();
    if (!value) return;
    requireAuth(() => {
      setStarted(null);
      start.mutate(value);
    });
  }

  const result = job.data?.status === "done" ? job.data.result : null;
  const doneSlug = started?.slug || String(result?.slug ?? "");
  const doneTitle = started?.title || String(result?.title ?? doneSlug);
  const failed = job.data?.status === "failed";
  const waiting =
    start.isPending || (Boolean(jobId) && !doneSlug && !failed && !job.isError && !timedOut);
  const requestError = start.error as ApiError | null;
  // Our own words for known codes (is_modpack, hidden_project…), else the API's field message
  const inputError = requestError
    ? (copy.errors[requestError.code] ?? fieldErrors(requestError).url ?? copy.errors.failed)
    : undefined;

  return (
    <section className="flex flex-col gap-4 border-t border-line pt-10">
      <h2 className="font-display text-h2">{copy.title}</h2>
      <p className="max-w-prose text-muted">{copy.text}</p>
      <form onSubmit={submit} className="flex flex-col gap-3 sm:flex-row sm:items-start">
        <div className="min-w-0 flex-1">
          <Input
            label={copy.label}
            hideLabel
            placeholder={copy.placeholder}
            value={url}
            onChange={(event) => setUrl(event.target.value)}
            error={inputError}
            autoComplete="off"
          />
        </div>
        <Button type="submit" variant="secondary" size="lg" loading={waiting}>
          {copy.submit}
        </Button>
      </form>
      <p role="status" aria-live="polite" className="text-meta text-muted">
        {waiting && copy.pending}
        {doneSlug && (
          <>
            {copy.done(doneTitle)}{" "}
            <Link href={`/mods/${doneSlug}`} className="underline underline-offset-4">
              {copy.open}
            </Link>
          </>
        )}
        {(failed || job.isError) && (
          <span className="text-danger">{errorText(job.data?.error)}</span>
        )}
        {timedOut && !doneSlug && !failed && (
          <span className="text-danger">{copy.errors.timeout}</span>
        )}
      </p>
    </section>
  );
}
