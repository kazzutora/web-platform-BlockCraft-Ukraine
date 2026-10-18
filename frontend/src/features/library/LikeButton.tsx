"use client";

import { useMutation } from "@tanstack/react-query";
import { useState } from "react";

import { Icon } from "@/components/ui/Icon";
import { useToast } from "@/components/ui/useToast";
import { useRequireAuth } from "@/features/auth/useRequireAuth";
import { api } from "@/lib/api/client";
import { cn } from "@/lib/cn";

import { libraryCopy } from "./copy";
import type { Kind } from "./types";

type LikeButtonProps = { kind: Kind; id: string; liked: boolean; count: number };

/** Optimistic like with a counter (for kinds rated by likes). */
export function LikeButton({
  kind,
  id,
  liked: initialLiked,
  count: initialCount,
}: LikeButtonProps) {
  const toast = useToast();
  const requireAuth = useRequireAuth();
  const [state, setState] = useState({ liked: initialLiked, count: initialCount });

  const mutation = useMutation({
    mutationFn: async (next: boolean) => {
      const body = { kind, id };
      const { data, response } = next
        ? await api.POST("/api/v1/likes", { body })
        : await api.DELETE("/api/v1/likes", { params: { query: body } });
      if (!data) throw new Error(`likes: ${response.status}`);
      return data;
    },
    onMutate: (next) => {
      const previous = state;
      setState({ liked: next, count: Math.max(0, state.count + (next ? 1 : -1)) });
      return previous;
    },
    onError: (_error, _next, previous) => {
      if (previous) setState(previous);
      toast({ title: libraryCopy.save.error, tone: "danger" });
    },
    onSuccess: (data) => setState({ liked: data.liked, count: data.likes_count }),
  });

  return (
    <button
      type="button"
      aria-pressed={state.liked}
      aria-label={libraryCopy.collection.like}
      onClick={() => requireAuth(() => mutation.mutate(!state.liked))}
      className={cn(
        "inline-flex h-11 items-center gap-2 border px-4 text-sm transition-colors",
        state.liked ? "border-text bg-text text-bg" : "border-line hover:border-text",
      )}
    >
      <Icon name="heart" />
      <span className="tabular-nums">{state.count}</span>
    </button>
  );
}
