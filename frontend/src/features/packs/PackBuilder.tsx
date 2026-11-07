"use client";

import { useMutation, useMutationState, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";

import { Container } from "@/components/layout/Container";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { ButtonLink } from "@/components/ui/ButtonLink";
import { Chip } from "@/components/ui/Chip";
import { Tabs } from "@/components/ui/Tabs";
import { useToast } from "@/components/ui/useToast";
import type { ProjectCard } from "@/features/mods/types";
import { api } from "@/lib/api/client";
import { generalError } from "@/lib/api/errors";
import { queryKeys } from "@/lib/query-keys";

import { packsCopy } from "./copy";
import { CoverField } from "./CoverField";
import { Inventory } from "./Inventory";
import { ModSearch } from "./ModSearch";
import { PackForm, valuesOf } from "./PackForm";
import { PackIssues } from "./PackIssues";
import type { PackDetail } from "./types";
import { usePackItems } from "./usePackItems";

const copy = packsCopy.builder;
/** Background imports of missing dependencies take seconds: look again this many times. */
const DEPENDENCY_CHECKS = 8;

function waitingForDependencies(pack: PackDetail | undefined): boolean {
  return Boolean(pack?.issues.some((issue) => issue.other_modrinth_id));
}

/** /packs/[slug]/edit: search on the left, the inventory on the right, settings in a tab. */
export function PackBuilder({ initial }: { initial: PackDetail }) {
  const router = useRouter();
  const toast = useToast();
  const queryClient = useQueryClient();
  const key = queryKeys.packs.detail(initial.slug);
  const { data: pack = initial } = useQuery({
    queryKey: key,
    initialData: initial,
    queryFn: async () => {
      const { data } = await api.GET("/api/v1/packs/{slug}", {
        params: { path: { slug: initial.slug } },
      });
      if (!data) throw new Error("GET pack failed");
      return data;
    },
    refetchInterval: (query) =>
      waitingForDependencies(query.state.data) && query.state.dataUpdateCount < DEPENDENCY_CHECKS
        ? 4000
        : false,
  });
  const { add, remove, setRequired } = usePackItems(pack.slug);
  const pending = new Set(
    useMutationState({
      filters: { mutationKey: queryKeys.packs.adding(pack.slug), status: "pending" },
      select: (mutation) => (mutation.state.variables as ProjectCard).slug,
    }),
  );

  const publish = useMutation({
    mutationFn: async () => {
      const { data, error } = await api.POST("/api/v1/packs/{slug}/publish", {
        params: { path: { slug: pack.slug } },
      });
      if (!data) throw error;
      return data;
    },
    onError: (error) => toast({ title: generalError(error, copy.publishError), tone: "danger" }),
    onSuccess: (data) => {
      queryClient.setQueryData(key, data);
      void queryClient.invalidateQueries({ queryKey: queryKeys.packs.all });
      toast({ title: data.status === "published" ? copy.published : copy.pending });
      router.refresh();
    },
  });
  const canPublish = pack.status === "draft" || pack.status === "rejected";

  return (
    <Container className="flex flex-col gap-10 py-12 md:py-16">
      <header className="flex flex-col gap-6">
        <div className="flex flex-wrap items-center gap-3">
          <Chip tone="packs">{copy.chip}</Chip>
          <Badge tone={pack.status === "published" ? "accent" : "neutral"}>
            {copy.status[pack.status]}
          </Badge>
          <span className="text-meta text-muted">
            {copy.target(pack.game_version, packsCopy.loaders[pack.loader])}
          </span>
        </div>
        <h1 className="text-h1">{pack.title}</h1>
        {pack.status === "rejected" && pack.rejection_reason && (
          <p className="text-danger">{packsCopy.detail.rejected(pack.rejection_reason)}</p>
        )}
        <div className="flex flex-wrap gap-3">
          {canPublish && (
            <Button size="lg" loading={publish.isPending} onClick={() => publish.mutate()}>
              {copy.publish}
            </Button>
          )}
          <ButtonLink href={`/packs/${pack.slug}`} variant="secondary" size="lg">
            {copy.view}
          </ButtonLink>
        </div>
      </header>

      <PackIssues issues={pack.issues} />

      <Tabs
        label={copy.tabsLabel}
        items={[
          {
            value: "mods",
            label: copy.tabs.mods,
            content: (
              <div className="grid gap-12 md:grid-cols-2 md:gap-10">
                <ModSearch pack={pack} onAdd={(project) => add.mutate(project)} />
                <Inventory
                  items={pack.items}
                  pending={pending}
                  onRemove={(project) => remove.mutate(project)}
                  onRequiredChange={(project, required) =>
                    setRequired.mutate({ project, required })
                  }
                />
              </div>
            ),
          },
          {
            value: "settings",
            label: copy.tabs.settings,
            content: (
              <div className="flex max-w-xl flex-col gap-12">
                <CoverField pack={pack} onChange={(data) => queryClient.setQueryData(key, data)} />
                <PackForm
                  initial={valuesOf(pack)}
                  submitLabel={packsCopy.form.save}
                  onSubmit={async (body) => {
                    const { data, error } = await api.PATCH("/api/v1/packs/{slug}", {
                      params: { path: { slug: pack.slug } },
                      body,
                    });
                    if (!data) throw error;
                    queryClient.setQueryData(key, data);
                    toast({ title: packsCopy.form.saved });
                  }}
                />
              </div>
            ),
          },
        ]}
      />
    </Container>
  );
}
