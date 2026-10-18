"use client";

import { useQuery } from "@tanstack/react-query";

import { CardGrid } from "@/components/ui/CardGrid";
import { EmptyState } from "@/components/ui/EmptyState";
import { Skeleton } from "@/components/ui/Skeleton";
import { api } from "@/lib/api/client";
import { queryKeys } from "@/lib/query-keys";

import { CollectionCard } from "./CollectionCard";
import { libraryCopy } from "./copy";
import { NewCollectionButton } from "./NewCollectionButton";

/** /me/collections: own and shared-with-me collections. */
export function MyCollections() {
  const collections = useQuery({
    queryKey: queryKeys.library.myCollections(),
    queryFn: async () => {
      const { data } = await api.GET("/api/v1/me/collections");
      if (!data) throw new Error("me/collections");
      return data;
    },
  });

  return (
    <div className="flex flex-col gap-10">
      <div>
        <NewCollectionButton />
      </div>
      {collections.isPending ? (
        <CardGrid>
          {Array.from({ length: 4 }, (_, index) => (
            <Skeleton key={index} className="aspect-square w-full" />
          ))}
        </CardGrid>
      ) : collections.data?.length ? (
        <CardGrid>
          {collections.data.map((collection) => (
            <CollectionCard key={collection.id} collection={collection} showVisibility />
          ))}
        </CardGrid>
      ) : (
        <EmptyState title={libraryCopy.mine.empty} illustration="packs" />
      )}
    </div>
  );
}
