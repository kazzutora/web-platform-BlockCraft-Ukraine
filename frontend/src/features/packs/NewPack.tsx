"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";

import { Skeleton } from "@/components/ui/Skeleton";
import { useMe } from "@/features/auth/useMe";
import { gameVersions } from "@/features/game/labels";
import { api } from "@/lib/api/client";
import { queryKeys } from "@/lib/query-keys";

import { packsCopy } from "./copy";
import { PackForm, emptyPack } from "./PackForm";
import { packLoaders } from "./types";

/** /packs/new: a draft with a target, then straight to the constructor. */
export function NewPack() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { me, isLoading } = useMe();
  const profile = me?.game_profile;
  const loader = packLoaders.find((value) => value === profile?.loader);
  const gameVersion = gameVersions.find((value) => value === profile?.game_version);

  // The form starts from the player's game profile: wait for it instead of resetting
  // what was already typed
  if (isLoading) return <Skeleton className="h-96 w-full" />;

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
        await queryClient.invalidateQueries({ queryKey: queryKeys.packs.all });
        router.push(`/packs/${data.slug}/edit`);
      }}
    />
  );
}
