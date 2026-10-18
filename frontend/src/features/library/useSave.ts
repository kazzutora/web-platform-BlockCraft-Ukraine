"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { useToast } from "@/components/ui/useToast";
import { usePendingAction } from "@/features/auth/usePendingAction";
import { useRequireAuth } from "@/features/auth/useRequireAuth";
import { api } from "@/lib/api/client";
import { queryKeys } from "@/lib/query-keys";

import { libraryCopy } from "./copy";
import type { Kind } from "./types";

const copy = libraryCopy.save;

/**
 * Optimistic «save to favorites»: the slot fills at once, rolls back with a toast on error.
 * Guests get «Увійди, щоб не загубити» and the save happens after they come back.
 */
export function useSave(kind: Kind, id: string, initial: { saved: boolean; count?: number }) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const requireAuth = useRequireAuth();
  const [saved, setSaved] = useState(initial.saved);
  const [count, setCount] = useState(initial.count);
  const pendingKey = `save:${kind}:${id}`;

  const mutation = useMutation({
    mutationFn: async (next: boolean) => {
      const body = { kind, id };
      const { data, response } = next
        ? await api.POST("/api/v1/favorites", { body })
        : await api.DELETE("/api/v1/favorites", { params: { query: body } });
      if (!data) throw new Error(`favorites: ${response.status}`);
      return data;
    },
    onMutate: (next) => {
      const previous = { saved, count };
      setSaved(next);
      setCount((value) => (value === undefined ? value : Math.max(0, value + (next ? 1 : -1))));
      return previous;
    },
    onError: (_error, _next, previous) => {
      if (previous) {
        setSaved(previous.saved);
        setCount(previous.count);
      }
      toast({ title: copy.error, tone: "danger" });
    },
    onSuccess: (data) => {
      setSaved(data.favorited);
      setCount((value) => (value === undefined ? value : data.favorites_count));
      void queryClient.invalidateQueries({ queryKey: queryKeys.library.all });
    },
  });

  const toggle = () => requireAuth(() => mutation.mutate(!saved), { pendingKey });

  usePendingAction(pendingKey, () => {
    if (!saved) mutation.mutate(true);
  });

  return { saved, count, toggle, pending: mutation.isPending };
}
