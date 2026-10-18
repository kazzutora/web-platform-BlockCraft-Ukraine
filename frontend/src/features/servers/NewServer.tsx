"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";

import { useToast } from "@/components/ui/useToast";
import { api } from "@/lib/api/client";
import { queryKeys } from "@/lib/query-keys";

import { serversCopy } from "./copy";
import { ServerForm } from "./ServerForm";

const copy = serversCopy.form;

/** /servers/new: after saving, the page of the server (it gets pinged right away). */
export function NewServer() {
  const router = useRouter();
  const toast = useToast();
  const queryClient = useQueryClient();

  return (
    <ServerForm
      submitLabel={copy.submitNew}
      onSubmit={async (body) => {
        const { data, error } = await api.POST("/api/v1/servers", { body });
        if (!data) throw error;
        toast({ title: data.status === "published" ? copy.published : copy.pending });
        await queryClient.invalidateQueries({ queryKey: queryKeys.servers.all });
        router.push(`/servers/${data.slug}`);
      }}
    />
  );
}
