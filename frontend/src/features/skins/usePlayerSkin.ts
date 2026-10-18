"use client";

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import { queryKeys } from "@/lib/query-keys";

import type { LookupResult } from "./types";

export const NICKNAME = /^[A-Za-z0-9_]{3,16}$/;

export class LookupError extends Error {
  constructor(readonly status: number) {
    super(`skins/lookup: ${status}`);
  }
}

/** A Java player's skin through our cached Mojang proxy; idle for invalid nicknames. */
export function usePlayerSkin(nickname: string) {
  return useQuery({
    queryKey: queryKeys.skins.lookup(nickname),
    enabled: NICKNAME.test(nickname),
    staleTime: 10 * 60_000,
    retry: false,
    queryFn: async (): Promise<LookupResult> => {
      const { data, response } = await api.GET("/api/v1/skins/lookup", {
        params: { query: { nickname } },
      });
      if (!data) throw new LookupError(response.status);
      return data;
    },
  });
}
