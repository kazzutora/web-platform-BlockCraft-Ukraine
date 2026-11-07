"use client";

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import { queryKeys } from "@/lib/query-keys";

/** Supported versions for client forms, newest first; empty while /meta loads. */
export function useGameVersions(): string[] {
  const { data } = useQuery({
    queryKey: queryKeys.meta,
    queryFn: async () => {
      const { data, response } = await api.GET("/api/v1/meta");
      if (!data) throw new Error(`GET /api/v1/meta failed: ${response.status}`);
      return data;
    },
    staleTime: 10 * 60 * 1000,
  });
  return data?.game_versions.map((item) => item.version) ?? [];
}
