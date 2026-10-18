"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useCallback } from "react";

import { auth } from "@/lib/api/auth-client";
import { setSessionHint } from "@/lib/session-hint";

export function useLogout() {
  const queryClient = useQueryClient();
  const router = useRouter();

  return useCallback(async () => {
    // allauth answers 401 once the session is gone
    await auth.DELETE("/_allauth/browser/v1/auth/session");
    setSessionHint(false);
    queryClient.clear();
    router.replace("/");
    router.refresh();
  }, [queryClient, router]);
}
