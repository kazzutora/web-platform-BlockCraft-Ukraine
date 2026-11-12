"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { type FormEvent, useEffect, useState } from "react";

import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { api } from "@/lib/api/client";
import { type ApiError, fieldErrors } from "@/lib/api/errors";
import { queryKeys } from "@/lib/query-keys";

import { skinsCopy } from "./copy";

const copy = skinsCopy.add;
const POLL_MS = 1500;
/** Mojang and MineSkin answer in seconds; after this the page stops waiting. */
const GIVE_UP_MS = 60_000;

type Body = { nickname: string } | { mineskin: string };
type Started = { jobId: string | null; skinId: number | null; title: string };

function errorText(code: string | undefined): string {
  return (code && copy.errors[code]) || copy.errors.failed;
}

/** /skins/add: a nickname or a MineSkin link → background import → a link to the skin. */
export function AddSkin({ initialNickname = "" }: { initialNickname?: string }) {
  const [nickname, setNickname] = useState(initialNickname);
  const [mineskin, setMineskin] = useState("");
  const [started, setStarted] = useState<Started | null>(null);

  const start = useMutation({
    mutationFn: async (body: Body): Promise<Started> => {
      const { data, error } = await api.POST("/api/v1/skins", { body });
      if (error) throw error;
      return { jobId: data.job_id ?? null, skinId: data.id ?? null, title: data.title ?? "" };
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
    queryKey: queryKeys.skins.addJob(jobId),
    enabled: Boolean(jobId),
    queryFn: async () => {
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

  function submit(event: FormEvent, body: Body) {
    event.preventDefault();
    setStarted(null);
    start.mutate(body);
  }

  const result = job.data?.status === "done" ? job.data.result : null;
  const skinId = started?.skinId ?? (result ? Number(result.id) : null);
  const existing = started?.skinId != null || Boolean(result?.existing);
  const title = started?.title || String(result?.title ?? "");
  const failed = job.data?.status === "failed";
  const waiting = start.isPending || (Boolean(jobId) && !skinId && !failed && !timedOut);
  // The spinner belongs to the form that was sent
  const sentBy = start.variables && "mineskin" in start.variables ? "mineskin" : "nickname";
  const requestError = start.error as ApiError | null;
  const errors = requestError ? fieldErrors(requestError) : {};

  return (
    <div className="flex flex-col gap-10">
      <form
        onSubmit={(event) => submit(event, { nickname: nickname.trim() })}
        className="flex flex-col gap-3"
      >
        <h2 className="font-display text-h2">{copy.nicknameTitle}</h2>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start">
          <div className="min-w-0 flex-1">
            <Input
              label={copy.nickname}
              hideLabel
              placeholder="Steve"
              value={nickname}
              onChange={(event) => setNickname(event.target.value)}
              error={errors.nickname}
              autoComplete="off"
              spellCheck={false}
            />
          </div>
          <Button
            type="submit"
            size="lg"
            loading={waiting && sentBy === "nickname"}
            disabled={!nickname.trim() || waiting}
          >
            {copy.submit}
          </Button>
        </div>
      </form>

      <form
        onSubmit={(event) => submit(event, { mineskin: mineskin.trim() })}
        className="flex flex-col gap-3 border-t border-line pt-10"
      >
        <h2 className="font-display text-h2">{copy.mineskinTitle}</h2>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start">
          <div className="min-w-0 flex-1">
            <Input
              label={copy.mineskin}
              hideLabel
              placeholder={copy.mineskinPlaceholder}
              value={mineskin}
              onChange={(event) => setMineskin(event.target.value)}
              error={errors.mineskin}
              autoComplete="off"
              spellCheck={false}
            />
          </div>
          <Button
            type="submit"
            variant="secondary"
            size="lg"
            loading={waiting && sentBy === "mineskin"}
            disabled={!mineskin.trim() || waiting}
          >
            {copy.submit}
          </Button>
        </div>
      </form>

      <p role="status" aria-live="polite" className="min-h-6">
        {waiting && <span className="text-muted">{copy.pending}</span>}
        {skinId && (
          <>
            {title ? (existing ? copy.existing(title) : copy.done(title)) : null}{" "}
            <Link href={`/skins/${skinId}`} className="underline underline-offset-4">
              {copy.open}
            </Link>
          </>
        )}
        {failed && <span className="text-danger">{errorText(job.data?.error)}</span>}
        {timedOut && !skinId && !failed && <span className="text-danger">{copy.slow}</span>}
        {requestError && !Object.keys(errors).length && (
          <span className="text-danger">{errorText(requestError.code)}</span>
        )}
      </p>
    </div>
  );
}
