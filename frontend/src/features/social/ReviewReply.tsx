"use client";

import { useMutation } from "@tanstack/react-query";
import Link from "next/link";
import { type FormEvent, useState } from "react";

import { Button } from "@/components/ui/Button";
import { Textarea } from "@/components/ui/Textarea";
import { useToast } from "@/components/ui/useToast";
import { api } from "@/lib/api/client";
import { generalError } from "@/lib/api/errors";
import type { components } from "@/lib/api/schema";

import { socialCopy } from "./copy";

type Review = components["schemas"]["Review"];

const copy = socialCopy.reply;

/** The answer of the pack's author or the server's owner; they may write or change it. */
export function ReviewReply({ review }: { review: Review }) {
  const toast = useToast();
  const [text, setText] = useState(review.reply_text);
  const [shown, setShown] = useState({ text: review.reply_text, by: review.reply_by?.nickname });
  const [editing, setEditing] = useState(false);

  const save = useMutation({
    mutationFn: async (value: string) => {
      const { data, error } = await api.PUT("/api/v1/reviews/{id}/reply", {
        params: { path: { id: review.id } },
        body: { text: value },
      });
      if (!data) throw error;
      return data;
    },
    onSuccess: (data) => {
      setShown({ text: data.reply_text, by: data.reply_by?.nickname });
      setEditing(false);
      toast({ title: data.reply_text ? copy.saved : copy.removed });
    },
    onError: (error) => toast({ title: generalError(error, copy.error), tone: "danger" }),
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    save.mutate(text.trim());
  }

  return (
    <div className="flex flex-col gap-3">
      {shown.text && !editing && (
        <div className="ml-4 flex flex-col gap-1 border-l-2 border-line pl-4">
          <p className="text-meta text-muted">
            {copy.from}{" "}
            {shown.by && (
              <Link href={`/u/${shown.by}`} className="underline underline-offset-4">
                {shown.by}
              </Link>
            )}
          </p>
          <p className="max-w-prose whitespace-pre-line">{shown.text}</p>
        </div>
      )}
      {review.can_reply && !editing && (
        <Button variant="ghost" className="self-start px-0" onClick={() => setEditing(true)}>
          {shown.text ? copy.edit : copy.write}
        </Button>
      )}
      {editing && (
        <form onSubmit={submit} className="ml-4 flex flex-col gap-3 border-l-2 border-line pl-4">
          <Textarea
            label={copy.label}
            hint={copy.hint}
            maxLength={500}
            rows={3}
            value={text}
            onChange={(event) => setText(event.target.value)}
          />
          <div className="flex gap-3">
            <Button type="submit" loading={save.isPending}>
              {copy.submit}
            </Button>
            <Button variant="ghost" onClick={() => setEditing(false)}>
              {copy.cancel}
            </Button>
          </div>
        </form>
      )}
    </div>
  );
}
