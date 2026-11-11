"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";

import { Button } from "@/components/ui/Button";
import { ChoiceChips } from "@/components/ui/ChoiceChips";
import { Input } from "@/components/ui/Input";
import { Textarea } from "@/components/ui/Textarea";
import { useToast } from "@/components/ui/useToast";
import { useMe } from "@/features/auth/useMe";
import { useRequireAuth } from "@/features/auth/useRequireAuth";
import { api } from "@/lib/api/client";
import { fieldErrors, generalError } from "@/lib/api/errors";
import type { components } from "@/lib/api/schema";
import { queryKeys } from "@/lib/query-keys";

import { translationsCopy as copy } from "./copy";

type Kind = components["schemas"]["TranslationProposeRequest"]["kind"];
type Field = components["schemas"]["TranslationFieldEnum"];
type Translation = components["schemas"]["Translation"];

type TranslationBlockProps = {
  kind: Kind;
  id: string;
  /** Sanitized HTML from the source (Modrinth). */
  originalHtml: string;
  /** Sanitized HTML of the approved translation, if any. */
  ukrainianHtml: string;
  translator: string | null;
  noDescription: string;
};

/**
 * «Опис українською · переклав @нік» with «Показати оригінал»; anyone may propose a
 * translation (sign-in asked), moderators approve or reject pending ones right here.
 */
export function TranslationBlock({
  kind,
  id,
  originalHtml,
  ukrainianHtml,
  translator,
  noDescription,
}: TranslationBlockProps) {
  const [original, setOriginal] = useState(!ukrainianHtml);
  const [proposing, setProposing] = useState(false);
  const requireAuth = useRequireAuth();
  const shownHtml = original ? originalHtml : ukrainianHtml;

  return (
    <div className="flex flex-col gap-6">
      {ukrainianHtml ? (
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line pb-3">
          <p className="text-meta text-muted">
            {original ? (
              copy.original
            ) : (
              <>
                {copy.ukrainian}
                {translator && (
                  <>
                    {` · ${copy.by} `}
                    <Link href={`/u/${translator}`} className="underline underline-offset-4">
                      @{translator}
                    </Link>
                  </>
                )}
              </>
            )}
          </p>
          <Button variant="ghost" className="px-0" onClick={() => setOriginal(!original)}>
            {original ? copy.showUkrainian : copy.showOriginal}
          </Button>
        </div>
      ) : (
        <div className="flex flex-wrap items-center justify-between gap-3 border border-line p-4">
          <p className="text-sm">{copy.missing}</p>
          {!proposing && (
            <Button variant="secondary" onClick={() => requireAuth(() => setProposing(true))}>
              {copy.propose}
            </Button>
          )}
        </div>
      )}
      {proposing && <ProposeForm kind={kind} id={id} onDone={() => setProposing(false)} />}
      {shownHtml ? (
        // Sanitized on the server (nh3): from the source when synced, ours when approved
        <div className="rich-text" dangerouslySetInnerHTML={{ __html: shownHtml }} />
      ) : (
        <p className="text-muted">{noDescription}</p>
      )}
      {ukrainianHtml && !proposing && (
        <Button
          variant="ghost"
          className="self-start px-0"
          onClick={() => requireAuth(() => setProposing(true))}
        >
          {copy.improve}
        </Button>
      )}
      <TranslationList kind={kind} id={id} />
    </div>
  );
}

function ProposeForm({ kind, id, onDone }: { kind: Kind; id: string; onDone: () => void }) {
  const toast = useToast();
  const queryClient = useQueryClient();
  const [field, setField] = useState<Field>("description");
  const [text, setText] = useState("");

  const send = useMutation({
    mutationFn: async () => {
      const { data, error } = await api.POST("/api/v1/translations", {
        body: { kind, id, field, text: text.trim() },
      });
      if (!data) throw error;
      return data;
    },
    onSuccess: () => {
      toast({ title: copy.sent });
      void queryClient.invalidateQueries({ queryKey: queryKeys.translations.of(kind, id) });
      onDone();
    },
  });
  const errorText = send.error
    ? (fieldErrors(send.error).text ?? generalError(send.error, copy.error))
    : undefined;

  function submit(event: FormEvent) {
    event.preventDefault();
    if (text.trim()) send.mutate();
  }

  return (
    <form onSubmit={submit} className="flex flex-col gap-4 border border-line p-4">
      <ChoiceChips
        label={copy.field}
        options={(["description", "summary"] as const).map((value) => ({
          value,
          label: copy.fields[value],
        }))}
        value={field}
        onChange={setField}
      />
      {field === "summary" ? (
        <Input
          label={copy.text}
          hint={copy.textHint.summary}
          maxLength={300}
          value={text}
          onChange={(event) => setText(event.target.value)}
          error={errorText}
        />
      ) : (
        <Textarea
          label={copy.text}
          hint={copy.textHint.description}
          maxLength={20000}
          rows={10}
          value={text}
          onChange={(event) => setText(event.target.value)}
          error={errorText}
        />
      )}
      <div className="flex flex-wrap gap-3">
        <Button type="submit" loading={send.isPending} disabled={!text.trim()}>
          {copy.submit}
        </Button>
        <Button variant="ghost" onClick={onDone}>
          {copy.cancel}
        </Button>
      </div>
    </form>
  );
}

/** My pending and rejected translations; for moderators — everything waiting, with buttons. */
function TranslationList({ kind, id }: { kind: Kind; id: string }) {
  const { me } = useMe();
  const rows = useQuery({
    queryKey: queryKeys.translations.of(kind, id),
    enabled: Boolean(me),
    queryFn: async () => {
      const { data } = await api.GET("/api/v1/translations", { params: { query: { kind, id } } });
      return data ?? [];
    },
  });
  const moderator = me?.role === "moderator" || me?.role === "admin";
  const waiting = (rows.data ?? []).filter(
    (row) => row.status !== "published" && (moderator || row.author.nickname === me?.nickname),
  );
  if (!waiting.length) return null;

  return (
    <section className="flex flex-col gap-3 border-t border-line pt-6">
      <h3 className="caps font-sans text-muted">{moderator ? copy.queue : copy.mine}</h3>
      <ul className="flex flex-col gap-4">
        {waiting.map((row) => (
          <TranslationRow key={row.id} row={row} kind={kind} id={id} moderator={moderator} />
        ))}
      </ul>
    </section>
  );
}

function TranslationRow({
  row,
  kind,
  id,
  moderator,
}: {
  row: Translation;
  kind: Kind;
  id: string;
  moderator: boolean;
}) {
  const toast = useToast();
  const queryClient = useQueryClient();
  const router = useRouter();
  const [reason, setReason] = useState("");

  const decide = useMutation({
    mutationFn: async (decision: "approve" | "reject") => {
      const { data, error } = await api.POST("/api/v1/translations/{id}/review", {
        params: { path: { id: row.id } },
        body: { decision, reason },
      });
      if (!data) throw error;
      return data;
    },
    onSuccess: () => {
      toast({ title: copy.decided });
      void queryClient.invalidateQueries({ queryKey: queryKeys.translations.of(kind, id) });
      // The approved text is rendered on the server
      router.refresh();
    },
    onError: (error) => toast({ title: generalError(error, copy.error), tone: "danger" }),
  });

  return (
    <li className="flex flex-col gap-2 border border-line p-4">
      <p className="text-meta text-muted">
        {copy.fields[row.field]} · @{row.author.nickname} · {copy.statuses[row.status]}
      </p>
      <p className="max-w-prose whitespace-pre-line">{row.text}</p>
      {row.status === "rejected" && row.reject_reason && (
        <p className="text-sm text-danger">{copy.rejectedBecause(row.reject_reason)}</p>
      )}
      {moderator && row.status === "pending" && (
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <div className="min-w-0 flex-1">
            <Input
              label={copy.rejectReason}
              maxLength={280}
              value={reason}
              onChange={(event) => setReason(event.target.value)}
            />
          </div>
          <Button loading={decide.isPending} onClick={() => decide.mutate("approve")}>
            {copy.approve}
          </Button>
          <Button variant="secondary" onClick={() => decide.mutate("reject")}>
            {copy.reject}
          </Button>
        </div>
      )}
    </li>
  );
}
