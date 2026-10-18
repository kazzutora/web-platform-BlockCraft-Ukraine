"use client";

import { useQuery } from "@tanstack/react-query";

import { auth } from "@/lib/api/auth-client";
import { queryKeys } from "@/lib/query-keys";

/** allauth configuration: which OAuth providers are set up on the server. */
export function useAuthConfig() {
  return useQuery({
    queryKey: queryKeys.auth.config,
    queryFn: async () => {
      const { data } = await auth.GET("/_allauth/browser/v1/config");
      return data?.data ?? null;
    },
    staleTime: Infinity,
  });
}
