"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/Button";
import { Icon } from "@/components/ui/Icon";
import { buttonClasses } from "@/components/ui/buttonClasses";
import { useToast } from "@/components/ui/useToast";
import { useRequireAuth } from "@/features/auth/useRequireAuth";
import { api } from "@/lib/api/client";
import { queryKeys } from "@/lib/query-keys";

import { packsCopy } from "./copy";

const copy = packsCopy.detail;

type PackActionsProps = { slug: string; official: boolean; canFork: boolean };

/** The main action (the .mrpack) and «make a copy» for players who want to change it. */
export function PackActions({ slug, official, canFork }: PackActionsProps) {
  const router = useRouter();
  const toast = useToast();
  const queryClient = useQueryClient();
  const requireAuth = useRequireAuth();

  const fork = useMutation({
    mutationFn: async () => {
      const { data, error } = await api.POST("/api/v1/packs/{slug}/fork", {
        params: { path: { slug } },
      });
      if (!data) throw error;
      return data;
    },
    onError: () => toast({ title: copy.error, tone: "danger" }),
    onSuccess: async (data) => {
      toast({ title: copy.forked });
      await queryClient.invalidateQueries({ queryKey: queryKeys.packs.all });
      router.push(`/packs/${data.slug}/edit`);
    },
  });

  return (
    <>
      {/* A plain link: the browser downloads the file (official packs go to Modrinth) */}
      <a
        href={`/api/v1/packs/${slug}/export.mrpack`}
        className={buttonClasses({ size: "lg" })}
        {...(official ? { rel: "noopener" } : { download: `${slug}.mrpack` })}
      >
        <Icon name="download" />
        {official ? copy.downloadOfficial : copy.download}
      </a>
      {canFork && (
        <Button
          variant="secondary"
          size="lg"
          loading={fork.isPending}
          onClick={() => requireAuth(() => fork.mutate())}
        >
          <Icon name="copy" />
          {copy.fork}
        </Button>
      )}
    </>
  );
}
