"use client";

import { useQuery } from "@tanstack/react-query";
import Image from "next/image";
import { useState } from "react";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { ChoiceChips } from "@/components/ui/ChoiceChips";
import { Illustration } from "@/components/ui/Illustration";
import { Input } from "@/components/ui/Input";
import { Skeleton } from "@/components/ui/Skeleton";
import { type ProjectCard, type ProjectType, projectTypes } from "@/features/mods/types";
import { useDebouncedValue } from "@/features/search/useDebouncedValue";
import { api } from "@/lib/api/client";
import { queryKeys } from "@/lib/query-keys";

import { packsCopy } from "./copy";
import type { PackDetail } from "./types";

const copy = packsCopy.builder;
const RESULTS = 12;

type ModSearchProps = {
  pack: PackDetail;
  onAdd: (project: ProjectCard) => void;
};

/** Left half of the constructor: catalog projects that have a file for the pack's target. */
export function ModSearch({ pack, onAdd }: ModSearchProps) {
  const [q, setQ] = useState("");
  const [type, setType] = useState<ProjectType>("mod");
  const query = {
    q: useDebouncedValue(q.trim(), 300),
    type,
    game_version: pack.game_version,
    loader: pack.loader,
  };
  const results = useQuery({
    queryKey: queryKeys.packs.search(query),
    queryFn: async () => {
      const { data } = await api.GET("/api/v1/mods", {
        params: { query: { ...query, q: query.q || undefined, page_size: RESULTS } },
      });
      if (!data) throw new Error("GET /api/v1/mods failed");
      return data.results;
    },
    placeholderData: (previous) => previous,
  });
  const inPack = new Set(pack.items.map((item) => item.project.slug));

  return (
    <section aria-labelledby="mod-search" className="flex min-w-0 flex-col gap-5">
      <h2 id="mod-search" className="text-h2">
        {copy.search}
      </h2>
      <Input
        label={copy.search}
        hideLabel
        type="search"
        placeholder={copy.searchPlaceholder}
        hint={copy.searchHint}
        value={q}
        onChange={(event) => setQ(event.target.value)}
      />
      <ChoiceChips
        label={copy.search}
        hideLabel
        options={projectTypes.map((value) => ({ value, label: copy.types[value] }))}
        value={type}
        onChange={setType}
      />
      {results.isPending ? (
        <ul className="flex flex-col gap-3">
          {Array.from({ length: 4 }, (_, index) => (
            <li key={index}>
              <Skeleton className="h-16 w-full" />
            </li>
          ))}
        </ul>
      ) : results.isError ? (
        <div className="flex flex-col items-start gap-3">
          <p className="text-muted">{copy.searchError}</p>
          <Button variant="secondary" onClick={() => void results.refetch()}>
            {copy.retry}
          </Button>
        </div>
      ) : results.data.length ? (
        <ul className="flex flex-col divide-y divide-line border-y border-line">
          {results.data.map((project) => (
            <li key={project.slug} className="flex items-center gap-4 py-3">
              <span className="relative size-12 shrink-0 border border-line bg-surface">
                {project.icon_url ? (
                  <Image
                    src={project.icon_url}
                    alt=""
                    fill
                    sizes="48px"
                    className="object-contain p-1"
                  />
                ) : (
                  <Illustration name="mods" size={44} />
                )}
              </span>
              <span className="flex min-w-0 flex-1 flex-col">
                <span className="truncate font-medium">{project.title}</span>
                <span className="truncate text-meta text-muted">{project.summary}</span>
              </span>
              {inPack.has(project.slug) ? (
                <Badge icon="check">{copy.inPack}</Badge>
              ) : (
                <Button variant="secondary" onClick={() => onAdd(project)}>
                  {copy.add}
                </Button>
              )}
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-muted">{copy.noResults}</p>
      )}
    </section>
  );
}
