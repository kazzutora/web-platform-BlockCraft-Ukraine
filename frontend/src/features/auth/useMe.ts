"use client";

import { useQuery } from "@tanstack/react-query";
import { useSyncExternalStore } from "react";

import { api } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";
import { queryKeys } from "@/lib/query-keys";
import { hasSessionHint, setSessionHint, subscribeSessionHint } from "@/lib/session-hint";

export type Me = components["schemas"]["Me"];

/** null while rendering on the server: the hint is known only in the browser. */
export function useSessionHint(): boolean | null {
  return useSyncExternalStore(subscribeSessionHint, hasSessionHint, () => null);
}

/** Current user or null for guests. Guests never hit /api/v1/me. */
export function useMe() {
  const hinted = useSessionHint();

  const query = useQuery({
    queryKey: queryKeys.me.account(),
    enabled: hinted === true,
    queryFn: async (): Promise<Me | null> => {
      const { data, response } = await api.GET("/api/v1/me");
      if (response.status === 401) {
        setSessionHint(false);
        return null;
      }
      if (!data) throw new Error(`GET /api/v1/me failed: ${response.status}`);
      return data;
    },
    staleTime: 60_000,
  });

  return {
    me: hinted ? (query.data ?? null) : null,
    isGuest: hinted === false || query.data === null,
    isLoading: hinted === null || (hinted && query.isPending),
  };
}
