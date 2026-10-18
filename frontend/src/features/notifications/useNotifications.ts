"use client";

import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useMe } from "@/features/auth/useMe";
import { api } from "@/lib/api/client";
import { queryKeys } from "@/lib/query-keys";

const POLL_MS = 60_000;

/** Unread count for the bell: asked every 60 seconds while the tab is visible. */
export function useUnreadCount() {
  const { me } = useMe();
  return useQuery({
    queryKey: queryKeys.notifications.unread(),
    enabled: Boolean(me),
    refetchInterval: POLL_MS,
    queryFn: async () => {
      const { data } = await api.GET("/api/v1/me/notifications/unread");
      return data?.unread_count ?? 0;
    },
  });
}

export function useNotifications(enabled = true) {
  return useInfiniteQuery({
    queryKey: queryKeys.notifications.list(),
    enabled,
    initialPageParam: 1,
    queryFn: async ({ pageParam }) => {
      const { data } = await api.GET("/api/v1/me/notifications", {
        params: { query: { page: pageParam } },
      });
      if (!data) throw new Error("GET /api/v1/me/notifications failed");
      return data;
    },
    getNextPageParam: (last) => last.next_page ?? undefined,
  });
}

/** Marks some (or, without ids, all) notifications read and updates the bell at once. */
export function useMarkRead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (ids?: number[]) => {
      const { data } = await api.POST("/api/v1/me/notifications/read", {
        body: ids ? { ids } : {},
      });
      return data?.unread_count ?? 0;
    },
    onSuccess: (count) => {
      queryClient.setQueryData(queryKeys.notifications.unread(), count);
      void queryClient.invalidateQueries({ queryKey: queryKeys.notifications.list() });
    },
  });
}
