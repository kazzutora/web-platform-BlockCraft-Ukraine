"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { useToast } from "@/components/ui/useToast";
import type { ProjectCard } from "@/features/mods/types";
import { api } from "@/lib/api/client";
import { fieldErrors, generalError } from "@/lib/api/errors";
import { queryKeys } from "@/lib/query-keys";

import { packsCopy } from "./copy";
import type { PackDetail, PackItem } from "./types";

const copy = packsCopy.builder;

type Snapshot = { previous?: PackDetail };

function placeholder(project: ProjectCard): PackItem {
  return {
    project: {
      slug: project.slug,
      title: project.title,
      icon_url: project.icon_url,
      project_type: project.project_type,
      summary: project.summary,
    },
    version: null,
    reason: "requested",
    required_by: [],
    env_client: "required",
    env_server: "required",
  };
}

/**
 * Constructor mutations on the cached pack: the set changes at once and rolls back with a
 * toast if the server says no. The server answer replaces the guess: it carries the
 * resolved dependencies and the new compatibility report.
 */
export function usePackItems(slug: string) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const key = queryKeys.packs.detail(slug);

  function optimistic(change: (pack: PackDetail) => PackDetail) {
    return async (): Promise<Snapshot> => {
      await queryClient.cancelQueries({ queryKey: key });
      const previous = queryClient.getQueryData<PackDetail>(key);
      if (previous) queryClient.setQueryData(key, change(previous));
      return { previous };
    };
  }

  function rollback(fallback: string) {
    return (error: unknown, _variables: unknown, context?: Snapshot) => {
      if (context?.previous) queryClient.setQueryData(key, context.previous);
      toast({
        title: fieldErrors(error).project ?? generalError(error, fallback),
        tone: "danger",
      });
    };
  }

  const settle = (data: PackDetail) => {
    queryClient.setQueryData(key, data);
    void queryClient.invalidateQueries({ queryKey: queryKeys.packs.mine() });
  };

  const add = useMutation({
    mutationKey: queryKeys.packs.adding(slug),
    mutationFn: async (project: ProjectCard) => {
      const { data, error } = await api.POST("/api/v1/packs/{slug}/items", {
        params: { path: { slug } },
        body: { project: project.slug },
      });
      if (!data) throw error;
      return data;
    },
    onMutate: (project) =>
      optimistic((pack) => {
        // Already pulled in as a dependency: it becomes the author's pick, not a new row
        if (pack.items.some((item) => item.project.slug === project.slug)) {
          return {
            ...pack,
            items: pack.items.map((item) =>
              item.project.slug === project.slug ? { ...item, reason: "requested" } : item,
            ),
          };
        }
        return {
          ...pack,
          items: [...pack.items, placeholder(project)],
          items_count: pack.items_count + 1,
        };
      })(),
    onError: rollback(copy.addError),
    onSuccess: (data, _project, context) => {
      const before = context?.previous?.items.length ?? data.items.length - 1;
      const pulled = data.items.length - before - 1;
      if (pulled > 0) toast({ title: copy.added(pulled) });
      settle(data);
    },
  });

  const remove = useMutation({
    mutationFn: async (project: string) => {
      const { data, error } = await api.DELETE("/api/v1/packs/{slug}/items/{project_slug}", {
        params: { path: { slug, project_slug: project } },
      });
      if (!data) throw error;
      return data;
    },
    onMutate: (project) =>
      optimistic((pack) => ({
        ...pack,
        items: pack.items.filter((item) => item.project.slug !== project),
        items_count: Math.max(0, pack.items_count - 1),
      }))(),
    onError: rollback(copy.removeError),
    onSuccess: settle,
  });

  const setOptional = useMutation({
    mutationFn: async ({ project, optional }: { project: string; optional: boolean }) => {
      const { data, error } = await api.PATCH("/api/v1/packs/{slug}/items/{project_slug}", {
        params: { path: { slug, project_slug: project } },
        body: { optional },
      });
      if (!data) throw error;
      return data;
    },
    onMutate: ({ project, optional }) =>
      optimistic((pack) => ({
        ...pack,
        items: pack.items.map((item) =>
          item.project.slug === project
            ? {
                ...item,
                env_client: optional ? "optional" : "required",
                env_server: optional ? "optional" : "required",
              }
            : item,
        ),
      }))(),
    onError: rollback(packsCopy.detail.error),
    onSuccess: settle,
  });

  return { add, remove, setOptional };
}
