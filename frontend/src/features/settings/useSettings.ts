"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";
import { queryKeys } from "@/lib/query-keys";

export type UserSettings = components["schemas"]["UserSettings"];
type SettingsPatch = components["schemas"]["PatchedUserSettingsRequest"];
type AccountPatch = components["schemas"]["PatchedMeUpdateRequest"];
type GameProfilePatch = components["schemas"]["PatchedGameProfileRequest"];

/** Throws the API error body, so callers can map it onto fields. */
function unwrap<T>(result: { data?: T; error?: unknown }): T {
  if (result.error !== undefined || result.data === undefined) throw result.error ?? new Error();
  return result.data;
}

export function useSettings() {
  return useQuery({
    queryKey: queryKeys.me.settings(),
    queryFn: async () => unwrap(await api.GET("/api/v1/me/settings")),
  });
}

export function useUpdateSettings() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: SettingsPatch) =>
      unwrap(await api.PATCH("/api/v1/me/settings", { body })),
    onSuccess: (data) => queryClient.setQueryData(queryKeys.me.settings(), data),
  });
}

export function useUpdateAccount() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: AccountPatch) => unwrap(await api.PATCH("/api/v1/me", { body })),
    onSuccess: (data) => queryClient.setQueryData(queryKeys.me.account(), data),
  });
}

export function useUpdateGameProfile() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: GameProfilePatch) =>
      unwrap(await api.PATCH("/api/v1/me/game-profile", { body })),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: queryKeys.me.account() }),
  });
}

export function useAvatar() {
  const queryClient = useQueryClient();
  const onSuccess = (data: components["schemas"]["Me"]) =>
    queryClient.setQueryData(queryKeys.me.account(), data);
  const upload = useMutation({
    mutationFn: async (file: File) =>
      unwrap(
        await api.PUT("/api/v1/me/avatar", {
          body: { avatar: "" },
          bodySerializer: () => {
            const form = new FormData();
            form.append("avatar", file);
            return form;
          },
        }),
      ),
    onSuccess,
  });
  const remove = useMutation({
    mutationFn: async () => unwrap(await api.DELETE("/api/v1/me/avatar")),
    onSuccess,
  });
  return { upload, remove };
}
