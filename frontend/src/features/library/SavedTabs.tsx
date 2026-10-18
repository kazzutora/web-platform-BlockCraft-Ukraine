"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { ButtonLink } from "@/components/ui/ButtonLink";
import { CardGrid } from "@/components/ui/CardGrid";
import { EmptyState } from "@/components/ui/EmptyState";
import { FilterChip } from "@/components/ui/FilterChip";
import { FilterRow } from "@/components/ui/FilterRow";
import { Skeleton } from "@/components/ui/Skeleton";
import { Tabs } from "@/components/ui/Tabs";
import { useMe } from "@/features/auth/useMe";
import { ModCard } from "@/features/mods/ModCard";
import { api } from "@/lib/api/client";
import { queryKeys } from "@/lib/query-keys";

import { CollectionCard } from "./CollectionCard";
import { libraryCopy } from "./copy";

const copy = libraryCopy.saved;
type SavedKind = "mod" | "collection";

function SavedList({ kind, gameVersion }: { kind: SavedKind; gameVersion: string }) {
  const saved = useQuery({
    queryKey: queryKeys.library.saved(kind, gameVersion),
    queryFn: async () => {
      const { data } = await api.GET("/api/v1/me/saved", {
        params: {
          query: { kind, ...(gameVersion ? { game_version: gameVersion } : {}), page_size: 60 },
        },
      });
      if (!data) throw new Error("me/saved");
      return data;
    },
  });

  if (saved.isPending) {
    return (
      <CardGrid>
        {Array.from({ length: 4 }, (_, index) => (
          <Skeleton key={index} className="aspect-square w-full" />
        ))}
      </CardGrid>
    );
  }
  const items = saved.data?.results ?? [];
  if (!items.length) {
    return (
      <EmptyState
        title={copy.empty[kind]}
        illustration={kind === "mod" ? "mods" : "packs"}
        action={<ButtonLink href="/mods">{copy.browse[kind]}</ButtonLink>}
      />
    );
  }
  return (
    <CardGrid>
      {items.map((item) =>
        item.mod ? (
          <ModCard key={item.id} project={item.mod} />
        ) : item.collection ? (
          <CollectionCard key={item.id} collection={item.collection} />
        ) : null,
      )}
    </CardGrid>
  );
}

/** /me/saved: tabs by kind; mods can be narrowed to the player's version. */
export function SavedTabs() {
  const { me } = useMe();
  const profileVersion = me?.game_profile.game_version ?? "";
  const [onlyMine, setOnlyMine] = useState(false);
  const gameVersion = onlyMine ? profileVersion : "";

  return (
    <Tabs
      label={copy.tabsLabel}
      items={[
        {
          value: "mod",
          label: copy.tabs.mod,
          content: (
            <div className="flex flex-col gap-8">
              {profileVersion && (
                <FilterRow label={copy.tabs.mod}>
                  <FilterChip active={!onlyMine} onClick={() => setOnlyMine(false)}>
                    {copy.allVersions}
                  </FilterChip>
                  <FilterChip active={onlyMine} onClick={() => setOnlyMine(true)}>
                    {profileVersion}
                  </FilterChip>
                </FilterRow>
              )}
              <SavedList kind="mod" gameVersion={gameVersion} />
            </div>
          ),
        },
        {
          value: "collection",
          label: copy.tabs.collection,
          content: <SavedList kind="collection" gameVersion="" />,
        },
      ]}
    />
  );
}
