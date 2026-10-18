"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { Button } from "@/components/ui/Button";
import { Icon } from "@/components/ui/Icon";
import { useToast } from "@/components/ui/useToast";
import { api } from "@/lib/api/client";
import { queryKeys } from "@/lib/query-keys";

import { serversCopy } from "./copy";
import type { VerificationState } from "./types";

const copy = serversCopy.verify;

/** For the owner: the code for the MOTD and «Перевірити»; the check runs in the background. */
export function VerifyPanel({ slug, code }: { slug: string; code: string }) {
  const queryClient = useQueryClient();
  const router = useRouter();
  const toast = useToast();
  const key = queryKeys.servers.verification(slug);

  const state = useQuery({
    queryKey: key,
    queryFn: async (): Promise<VerificationState> => {
      const { data } = await api.GET("/api/v1/servers/{slug}/verify", {
        params: { path: { slug } },
      });
      return data?.state ?? "idle";
    },
    // While the worker pings the server, ask again every two seconds
    refetchInterval: (query) => (query.state.data === "checking" ? 2000 : false),
  });

  const check = useMutation({
    mutationFn: async () => {
      const { data } = await api.POST("/api/v1/servers/{slug}/verify", {
        params: { path: { slug } },
      });
      if (!data) throw new Error("POST verify failed");
      return data.state;
    },
    onSuccess: (next) => queryClient.setQueryData(key, next),
    onError: () => toast({ title: serversCopy.detail.error, tone: "danger" }),
  });

  const current = state.data ?? "idle";
  useEffect(() => {
    // The page shows «Перевірено» from the server render: refresh it once verified
    if (current === "verified") router.refresh();
  }, [current, router]);

  return (
    <section className="flex flex-col gap-4 border border-line p-6">
      <h2 className="caps font-sans">{copy.title}</h2>
      <ol className="flex list-decimal flex-col gap-2 pl-5">
        {copy.steps(code).map((step) => (
          <li key={step}>{step}</li>
        ))}
      </ol>
      <div className="flex flex-wrap items-center gap-3">
        <code className="border border-line px-3 py-2 font-mono text-sm">{code}</code>
        <Button
          variant="ghost"
          onClick={async () => {
            await navigator.clipboard.writeText(code).catch(() => {});
            toast({ title: serversCopy.copied(code) });
          }}
        >
          <Icon name="copy" />
          {copy.copyCode}
        </Button>
        <Button loading={check.isPending || current === "checking"} onClick={() => check.mutate()}>
          {copy.check}
        </Button>
      </div>
      {copy.states[current] && (
        <p role="status" className="text-sm">
          {copy.states[current]}
        </p>
      )}
    </section>
  );
}
