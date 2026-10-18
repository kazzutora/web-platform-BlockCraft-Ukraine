"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useCallback } from "react";

import { api } from "@/lib/api/client";
import { queryKeys } from "@/lib/query-keys";
import { setSessionHint } from "@/lib/session-hint";

import { safeNext } from "./next-url";

/**
 * After a successful sign-in: refresh the user, then go to `next` —
 * or to onboarding first if the player has not done it yet.
 */
export function useSignedIn() {
  const queryClient = useQueryClient();
  const router = useRouter();

  return useCallback(
    async (next?: string | null) => {
      setSessionHint(true);
      await queryClient.invalidateQueries({ queryKey: queryKeys.me.all });
      const { data: me } = await api.GET("/api/v1/me");
      const target = safeNext(next);
      const destination =
        me && !me.game_profile.onboarding_done
          ? `/welcome?next=${encodeURIComponent(target)}`
          : target;
      router.replace(destination);
      router.refresh();
    },
    [queryClient, router],
  );
}
