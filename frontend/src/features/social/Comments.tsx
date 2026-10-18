"use client";

import { useInfiniteQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { type FormEvent, useState } from "react";

import { Avatar } from "@/components/ui/Avatar";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Skeleton } from "@/components/ui/Skeleton";
import { Textarea } from "@/components/ui/Textarea";
import { useToast } from "@/components/ui/useToast";
import { useMe } from "@/features/auth/useMe";
import { useRequireAuth } from "@/features/auth/useRequireAuth";
import { ReportButton } from "@/features/moderation/ReportButton";
import type { Kind } from "@/features/library/types";
import { formatDate } from "@/features/mods/format";
import { api } from "@/lib/api/client";
import { fieldErrors, generalError } from "@/lib/api/errors";
import type { components } from "@/lib/api/schema";
import { queryKeys } from "@/lib/query-keys";

import { socialCopy } from "./copy";

const copy = socialCopy.comments;

type Comment = components["schemas"]["Comment"];
type Reply = components["schemas"]["CommentReply"];

function useRefresh(kind: Kind, id: string) {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: queryKeys.social.comments(kind, id) });
}

/** Thread under an object: pinned first, newest next, one level of replies. */
export function Comments({ kind, id }: { kind: Kind; id: string }) {
  const comments = useInfiniteQuery({
    queryKey: queryKeys.social.comments(kind, id),
    initialPageParam: "",
    queryFn: async ({ pageParam }) => {
      const { data } = await api.GET("/api/v1/comments", {
        params: { query: { kind, id, ...(pageParam ? { cursor: pageParam } : {}) } },
      });
      if (!data) throw new Error("comments");
      return data;
    },
    getNextPageParam: (last) => last.next_cursor ?? undefined,
  });

  if (comments.isPending) return <Skeleton className="h-40 w-full" />;
  if (!comments.data) return null;

  const first = comments.data.pages[0];
  const list = [...first.pinned, ...comments.data.pages.flatMap((page) => page.results)];

  return (
    <div className="flex max-w-prose flex-col gap-8">
      <NewComment kind={kind} id={id} canComment={first.can_comment} />
      {list.length ? (
        <ul className="flex flex-col">
          {list.map((comment) => (
            <CommentItem
              key={comment.id}
              comment={comment}
              kind={kind}
              id={id}
              canPin={first.can_pin}
              canReply={first.can_comment}
            />
          ))}
        </ul>
      ) : (
        <p className="text-muted">{copy.empty}</p>
      )}
      {comments.hasNextPage && (
        <Button
          variant="secondary"
          className="self-center"
          loading={comments.isFetchingNextPage}
          onClick={() => void comments.fetchNextPage()}
        >
          {copy.more}
        </Button>
      )}
    </div>
  );
}

function CommentForm({
  label,
  initial = "",
  submitLabel,
  onSubmit,
  onCancel,
}: {
  label: string;
  initial?: string;
  submitLabel: string;
  onSubmit: (body: string) => Promise<unknown>;
  onCancel?: () => void;
}) {
  const [body, setBody] = useState(initial);
  const [error, setError] = useState<string>();
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!body.trim()) return;
    setBusy(true);
    setError(undefined);
    try {
      await onSubmit(body.trim());
      setBody("");
    } catch (failure) {
      setError(fieldErrors(failure).body ?? generalError(failure, copy.error));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} noValidate className="flex flex-col gap-3">
      <Textarea
        label={label}
        hideLabel
        placeholder={copy.placeholder}
        maxLength={1000}
        rows={3}
        value={body}
        onChange={(event) => setBody(event.target.value)}
        error={error}
      />
      <div className="flex gap-3">
        <Button type="submit" loading={busy} disabled={!body.trim()}>
          {submitLabel}
        </Button>
        {onCancel && (
          <Button variant="ghost" onClick={onCancel}>
            {copy.cancel}
          </Button>
        )}
      </div>
    </form>
  );
}

function NewComment({ kind, id, canComment }: { kind: Kind; id: string; canComment: boolean }) {
  const requireAuth = useRequireAuth();
  const refresh = useRefresh(kind, id);
  const { me } = useMe();

  if (!canComment) {
    return !me ? (
      <Button
        variant="secondary"
        className="self-start"
        onClick={() => requireAuth(() => undefined)}
      >
        {copy.loginToComment}
      </Button>
    ) : (
      <p className="text-muted">{copy.closed}</p>
    );
  }
  return (
    <CommentForm
      label={copy.label}
      submitLabel={copy.submit}
      onSubmit={async (body) => {
        const { data, error } = await api.POST("/api/v1/comments", { body: { kind, id, body } });
        if (!data) throw error;
        await refresh();
      }}
    />
  );
}

function CommentItem({
  comment,
  kind,
  id,
  canPin,
  canReply,
}: {
  comment: Comment;
  kind: Kind;
  id: string;
  canPin: boolean;
  canReply: boolean;
}) {
  const refresh = useRefresh(kind, id);
  const [replying, setReplying] = useState(false);
  const pin = useMutation({
    mutationFn: () =>
      api.POST("/api/v1/comments/{id}/pin", { params: { path: { id: comment.id } } }),
    onSuccess: () => refresh(),
  });

  return (
    <li className="flex flex-col gap-4 border-b border-line py-6">
      <CommentBody comment={comment} kind={kind} id={id}>
        {comment.is_pinned && <Badge icon="flag">{copy.pinned}</Badge>}
        {!comment.is_deleted && canReply && (
          <Button variant="ghost" className="h-auto px-0" onClick={() => setReplying(true)}>
            {copy.reply}
          </Button>
        )}
        {canPin && !comment.is_deleted && (
          <Button
            variant="ghost"
            className="h-auto px-0"
            loading={pin.isPending}
            onClick={() => pin.mutate()}
          >
            {comment.is_pinned ? copy.unpin : copy.pin}
          </Button>
        )}
      </CommentBody>
      {(comment.replies.length > 0 || replying) && (
        <ul className="ml-6 flex flex-col gap-4 border-l border-line pl-4 sm:ml-10">
          {comment.replies.map((reply) => (
            <li key={reply.id}>
              <CommentBody comment={reply} kind={kind} id={id} />
            </li>
          ))}
          {replying && (
            <li>
              <CommentForm
                label={copy.replyLabel(comment.user.nickname)}
                submitLabel={copy.reply}
                onCancel={() => setReplying(false)}
                onSubmit={async (body) => {
                  const { data, error } = await api.POST("/api/v1/comments", {
                    body: { kind, id, body, parent: comment.id },
                  });
                  if (!data) throw error;
                  setReplying(false);
                  await refresh();
                }}
              />
            </li>
          )}
        </ul>
      )}
    </li>
  );
}

function CommentBody({
  comment,
  kind,
  id,
  children,
}: {
  comment: Comment | Reply;
  kind: Kind;
  id: string;
  children?: React.ReactNode;
}) {
  const toast = useToast();
  const refresh = useRefresh(kind, id);
  const [editing, setEditing] = useState(false);
  const remove = useMutation({
    mutationFn: () => api.DELETE("/api/v1/comments/{id}", { params: { path: { id: comment.id } } }),
    onSuccess: () => refresh(),
    onError: () => toast({ title: copy.error, tone: "danger" }),
  });

  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap items-center gap-3">
        <Avatar name={comment.user.nickname} src={comment.user.avatar_url} size={32} />
        <Link href={`/u/${comment.user.nickname}`} className="font-medium hover:underline">
          {comment.user.nickname}
        </Link>
        <span className="text-meta text-muted">
          {formatDate(comment.created_at)}
          {comment.is_edited && ` · ${copy.edited}`}
        </span>
      </div>
      {editing ? (
        <CommentForm
          label={copy.edit}
          initial={comment.body}
          submitLabel={copy.save}
          onCancel={() => setEditing(false)}
          onSubmit={async (body) => {
            const { data, error } = await api.PATCH("/api/v1/comments/{id}", {
              params: { path: { id: comment.id } },
              body: { body },
            });
            if (!data) throw error;
            setEditing(false);
            await refresh();
          }}
        />
      ) : comment.is_deleted ? (
        <p className="text-muted italic">{copy.deleted}</p>
      ) : (
        <p className="whitespace-pre-line">{comment.body}</p>
      )}
      {!editing && (
        <div className="flex flex-wrap items-center gap-4 text-sm">
          {children}
          {comment.can_edit && (
            <Button variant="ghost" className="h-auto px-0" onClick={() => setEditing(true)}>
              {copy.edit}
            </Button>
          )}
          {comment.can_delete && (
            <Button
              variant="ghost"
              className="h-auto px-0"
              loading={remove.isPending}
              onClick={() => remove.mutate()}
            >
              {copy.delete}
            </Button>
          )}
          {!comment.can_edit && !comment.is_deleted && (
            <ReportButton kind="comment" id={String(comment.id)} compact />
          )}
        </div>
      )}
    </div>
  );
}
