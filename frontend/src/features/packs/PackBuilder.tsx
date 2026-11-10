"use client";

import { useMutation, useMutationState, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useRef } from "react";

import { Container } from "@/components/layout/Container";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { ButtonLink } from "@/components/ui/ButtonLink";
import { Chip } from "@/components/ui/Chip";
import { CompatStatus } from "@/components/ui/CompatStatus";
import { Tabs } from "@/components/ui/Tabs";
import { useToast } from "@/components/ui/useToast";
import { ResolutionView } from "@/features/compat/ResolutionView";
import type { ProjectCard } from "@/features/mods/types";
import { api } from "@/lib/api/client";
import { generalError } from "@/lib/api/errors";
import { queryKeys } from "@/lib/query-keys";

import { packsCopy } from "./copy";
import { Inventory } from "./Inventory";
import { ModSearch } from "./ModSearch";
import { PackForm, valuesOf } from "./PackForm";
import { ShareLink } from "./ShareLink";
import type { PackDetail, PackVisibility } from "./types";
import { usePackItems } from "./usePackItems";

const copy = packsCopy.builder;
/** Background imports of missing dependencies take seconds: stop asking after a minute. */
const WAIT_MS = 60_000;
const TONES = { ok: "ok", warnings: "warning", errors: "error", unknown: "warning" } as const;

/** /packs/[slug]/edit: search on the left, the set on the right, the check on top. */
export function PackBuilder({ initial }: { initial: PackDetail }) {
  const router = useRouter();
  const toast = useToast();
  const queryClient = useQueryClient();
  const key = queryKeys.packs.detail(initial.slug);
  const waitingSince = useRef<number | null>(null);
  const { data: pack = initial } = useQuery({
    queryKey: key,
    initialData: initial,
    queryFn: async () => {
      // The check first: while dependencies are imported it resolves the set again
      await api.GET("/api/v1/packs/{slug}/check", { params: { path: { slug: initial.slug } } });
      const { data } = await api.GET("/api/v1/packs/{slug}", {
        params: { path: { slug: initial.slug } },
      });
      if (!data) throw new Error("GET pack failed");
      return data;
    },
    refetchInterval: (query) => {
      // Asks again while dependencies are imported, for a minute from when it started
      const waiting =
        query.state.data?.compat_status === "unknown" && query.state.data.items_count > 0;
      if (!waiting) {
        waitingSince.current = null;
        return false;
      }
      waitingSince.current ??= Date.now();
      return Date.now() - waitingSince.current < WAIT_MS ? 4000 : false;
    },
  });
  const { add, remove, setOptional } = usePackItems(pack.slug);
  const pending = new Set(
    useMutationState({
      filters: { mutationKey: queryKeys.packs.adding(pack.slug), status: "pending" },
      select: (mutation) => (mutation.state.variables as ProjectCard).slug,
    }),
  );

  const publish = useMutation({
    mutationFn: async (visibility: Exclude<PackVisibility, "private">) => {
      const { data, error } = await api.POST("/api/v1/packs/{slug}/publish", {
        params: { path: { slug: pack.slug } },
        body: { visibility },
      });
      if (!data) throw error;
      return data;
    },
    onError: (error) => toast({ title: generalError(error, copy.publishError), tone: "danger" }),
    onSuccess: (data) => {
      queryClient.setQueryData(key, data);
      void queryClient.invalidateQueries({ queryKey: queryKeys.packs.all });
      toast({ title: data.visibility === "link" ? copy.publishedLink : copy.published });
      router.refresh();
    },
  });
  const draft = pack.status === "draft" || pack.status === "rejected";
  const blocked = pack.compat_status === "errors" || pack.compat_status === "unknown";

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
          {pack.items_count > 0 && (
            <CompatStatus tone={TONES[pack.compat_status]}>
              {packsCopy.compat[pack.compat_status]}
            </CompatStatus>
          )}
        </div>
        <h1 className="text-h1">{pack.title}</h1>
        {pack.status === "rejected" && pack.rejection_reason && (
          <p className="text-danger">{packsCopy.detail.rejected(pack.rejection_reason)}</p>
        )}
        <div className="flex flex-wrap gap-3">
          {draft && (
            <>
              <Button
                size="lg"
                loading={publish.isPending && publish.variables === "public"}
                disabled={blocked}
                onClick={() => publish.mutate("public")}
              >
                {copy.publish}
              </Button>
              <Button
                variant="secondary"
                size="lg"
                loading={publish.isPending && publish.variables === "link"}
                disabled={blocked}
                onClick={() => publish.mutate("link")}
              >
                {copy.publishLink}
              </Button>
            </>
          )}
          <ButtonLink href={`/packs/${pack.slug}`} variant="ghost" size="lg">
            {copy.view}
          </ButtonLink>
        </div>
        {pack.visibility === "link" && pack.share_token && pack.status === "published" && (
          <ShareLink slug={pack.slug} token={pack.share_token} />
        )}
      </header>

      {pack.compat && pack.items_count > 0 && pack.compat.status !== "ok" && (
        <ResolutionView
          resolution={pack.compat}
          title={packsCopy.detail.tabs.check}
          mode="problems"
          live={false}
          downloads={false}
        />
      )}

      <Tabs
        label={copy.tabsLabel}
        items={[
          {
            value: "items",
            label: copy.tabs.items,
            content: (
              <div className="grid gap-12 md:grid-cols-2 md:gap-10">
                <ModSearch pack={pack} onAdd={(project) => add.mutate(project)} />
                <Inventory
                  items={pack.items}
                  pending={pending}
                  onRemove={(project) => remove.mutate(project)}
                  onOptionalChange={(project, optional) =>
                    setOptional.mutate({ project, optional })
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
