"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useRouter, useSearchParams } from "next/navigation";

import { Skeleton } from "@/components/ui/Skeleton";
import { useMe } from "@/features/auth/useMe";
import { useGameVersions } from "@/features/game/useGameVersions";
import { api } from "@/lib/api/client";
import { queryKeys } from "@/lib/query-keys";

import { packsCopy } from "./copy";
import { PackForm, emptyPack } from "./PackForm";
import { packLoaders } from "./types";

/** Projects passed by «Зробити збірку з цього» (`?items=sodium,iris`), at most a few. */
const MAX_PREFILL = 20;

/** /packs/new: a draft with a target, then straight to the constructor. */
export function NewPack() {
  const router = useRouter();
  const prefill = (useSearchParams().get("items") ?? "")
    .split(",")
    .map((slug) => slug.trim())
    .filter(Boolean)
    .slice(0, MAX_PREFILL);
  const queryClient = useQueryClient();
  const { me, isLoading } = useMe();
  const profile = me?.game_profile;
  const loader = packLoaders.find((value) => value === profile?.loader);
  const gameVersions = useGameVersions();
  const gameVersion =
    gameVersions.find((value) => value === profile?.game_version) ?? gameVersions[0];

  // The form starts from the player's game profile: wait for it instead of resetting
  // what was already typed
  if (isLoading || !gameVersions.length) return <Skeleton className="h-96 w-full" />;

  return (
    <PackForm
      short
      initial={{
        ...emptyPack,
        game_version: gameVersion ?? emptyPack.game_version,
        loader: loader ?? emptyPack.loader,
      }}
      submitLabel={packsCopy.form.create}
      onSubmit={async (body) => {
        const { data, error } = await api.POST("/api/v1/packs", { body });
        if (!data) throw error;
        // Dependencies come with each project; one that does not fit simply stays out
        for (const project of prefill) {
          await api.POST("/api/v1/packs/{slug}/items", {
            params: { path: { slug: data.slug } },
            body: { project },
          });
        }
        await queryClient.invalidateQueries({ queryKey: queryKeys.packs.all });
        router.push(`/packs/${data.slug}/edit`);
      }}
    />
  );
}
