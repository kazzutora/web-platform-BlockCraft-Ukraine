"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { ChoiceChips } from "@/components/ui/ChoiceChips";
import { Dialog } from "@/components/ui/Dialog";
import { Icon } from "@/components/ui/Icon";
import { Select } from "@/components/ui/Select";
import { Skeleton } from "@/components/ui/Skeleton";
import { useToast } from "@/components/ui/useToast";
import { useRequireAuth } from "@/features/auth/useRequireAuth";
import { useGameVersions } from "@/features/game/useGameVersions";
import { api } from "@/lib/api/client";
import { generalError } from "@/lib/api/errors";
import { queryKeys } from "@/lib/query-keys";

import { packsCopy } from "./copy";
import { type PackLoader, type Retarget, packLoaders } from "./types";

const copy = packsCopy.retarget;

type ForkDialogProps = {
  slug: string;
  gameVersion: string;
  loader: PackLoader;
  shareToken?: string;
};

/** «Зробити копію під 26.1»: shows what stays, changes and falls out, then makes a draft. */
export function ForkDialog({ slug, gameVersion, loader, shareToken = "" }: ForkDialogProps) {
  const router = useRouter();
  const toast = useToast();
  const queryClient = useQueryClient();
  const requireAuth = useRequireAuth();
  const versions = useGameVersions();
  const [open, setOpen] = useState(false);
  const [target, setTarget] = useState({ gameVersion, loader });
  const changed = target.gameVersion !== gameVersion || target.loader !== loader;
  const query = shareToken ? { share_token: shareToken } : {};

  const preview = useQuery({
    queryKey: queryKeys.packs.retarget(slug, target.gameVersion, target.loader),
    enabled: open && changed,
    queryFn: async (): Promise<Retarget> => {
      const { data } = await api.GET("/api/v1/packs/{slug}/retarget", {
        params: {
          path: { slug },
          query: { game_version: target.gameVersion, loader: target.loader, ...query },
        },
      });
      if (!data) throw new Error("retarget");
      return data;
    },
  });

  const fork = useMutation({
    mutationFn: async () => {
      const { data, error } = await api.POST("/api/v1/packs/{slug}/fork", {
        params: { path: { slug }, query },
        body: changed ? { game_version: target.gameVersion, loader: target.loader } : {},
      });
      if (!data) throw error;
      return data;
    },
    onError: (error) =>
      toast({ title: generalError(error, packsCopy.detail.error), tone: "danger" }),
    onSuccess: async (data) => {
      toast({ title: packsCopy.detail.forked });
      await queryClient.invalidateQueries({ queryKey: queryKeys.packs.all });
      router.push(`/packs/${data.slug}/edit`);
    },
  });

  return (
    <Dialog
      title={copy.title}
      description={copy.intro}
      open={open}
      onOpenChange={(next) => (next ? requireAuth(() => setOpen(true)) : setOpen(false))}
      trigger={
        <Button variant="secondary" size="lg">
          <Icon name="copy" />
          {packsCopy.detail.fork}
        </Button>
      }
      footer={
        <>
          <Button variant="ghost" onClick={() => setOpen(false)}>
            {packsCopy.detail.cancel}
          </Button>
          <Button loading={fork.isPending} onClick={() => fork.mutate()}>
            {copy.create}
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-5">
        <Select
          label={copy.version}
          value={target.gameVersion}
          options={versions.map((value) => ({ value, label: value }))}
          onChange={(event) => setTarget({ ...target, gameVersion: event.target.value })}
        />
        <ChoiceChips
          label={copy.loader}
          options={packLoaders.map((value) => ({ value, label: packsCopy.loaders[value] }))}
          value={target.loader}
          onChange={(value) => setTarget({ ...target, loader: value })}
        />
        {changed && <Preview state={preview} />}
      </div>
    </Dialog>
  );
}

function Preview({ state }: { state: ReturnType<typeof useQuery<Retarget>> }) {
  if (state.isPending) return <Skeleton className="h-32 w-full" />;
  if (state.isError || !state.data) return <p className="text-sm text-danger">{copy.error}</p>;
  const diff = state.data;
  const name = (slug: string) => diff.titles[slug] ?? slug;
  const groups = [
    { label: copy.dropped, names: diff.dropped.map(name), tone: "text-danger" },
    { label: copy.changed, names: diff.changed.map((row) => name(row.project)), tone: "" },
    { label: copy.added, names: diff.added.map(name), tone: "" },
    { label: copy.kept, names: diff.kept.map(name), tone: "text-muted" },
  ];
  return (
    <dl className="flex flex-col gap-3 text-sm" aria-live="polite">
      {groups.map((group) => (
        <div key={group.label} className="flex flex-col gap-1 border-t border-line pt-2">
          <dt className="text-meta text-muted">
            {group.label} · {group.names.length}
          </dt>
          <dd className={group.tone}>
            {group.names.length ? group.names.join(", ") : copy.nothing}
          </dd>
        </div>
      ))}
    </dl>
  );
}
