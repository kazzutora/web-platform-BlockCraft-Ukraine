"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { api } from "@/lib/api/client";
import { queryKeys } from "@/lib/query-keys";

import type { Resolution } from "./api";

const EVERY_MS = 4000;
/** Imports take seconds; after ~1 minute the page stops asking and keeps what it has. */
const TIMES = 15;

type ResolutionPollerProps = { slug: string; target: Resolution["target"] };

/**
 * Dependencies are being imported from Modrinth (`incomplete`): asks only the install
 * endpoint until the answer is complete, then re-renders the page once.
 */
export function ResolutionPoller({ slug, target }: ResolutionPollerProps) {
  const router = useRouter();
  const install = useQuery({
    queryKey: queryKeys.compat.install(slug, target.game_version, target.loader),
    queryFn: async () => {
      const { data } = await api.GET("/api/v1/mods/{slug}/install", {
        params: {
          path: { slug },
          query: { game_version: target.game_version, loader: target.loader },
        },
      });
      if (!data) throw new Error("install");
      return data;
    },
    refetchInterval: (query) =>
      query.state.data?.status === "incomplete" && query.state.dataUpdateCount < TIMES
        ? EVERY_MS
        : false,
  });
  const status = install.data?.status;

  useEffect(() => {
    if (status && status !== "incomplete") router.refresh();
  }, [status, router]);

  return null;
}
