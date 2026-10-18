"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { ButtonLink } from "@/components/ui/ButtonLink";
import { Dialog } from "@/components/ui/Dialog";
import { Icon } from "@/components/ui/Icon";
import { useToast } from "@/components/ui/useToast";
import { api } from "@/lib/api/client";
import { queryKeys } from "@/lib/query-keys";

import { serversCopy } from "./copy";

const copy = serversCopy.detail;

/** For the owner: edit the listing or delete it. */
export function ServerOwnerActions({ slug }: { slug: string }) {
  const router = useRouter();
  const toast = useToast();
  const queryClient = useQueryClient();
  const [deleting, setDeleting] = useState(false);

  const remove = useMutation({
    mutationFn: async () => {
      const { response } = await api.DELETE("/api/v1/servers/{slug}", {
        params: { path: { slug } },
      });
      if (!response.ok) throw new Error(`DELETE /api/v1/servers/${slug}: ${response.status}`);
    },
    onError: () => toast({ title: copy.error, tone: "danger" }),
    onSuccess: async () => {
      toast({ title: copy.deleted });
      await queryClient.invalidateQueries({ queryKey: queryKeys.servers.all });
      router.push("/me/works");
    },
  });

  return (
    <>
      <ButtonLink href={`/servers/${slug}/edit`} variant="secondary" size="lg">
        <Icon name="pencil" />
        {copy.edit}
      </ButtonLink>
      <Dialog
        title={copy.deleteTitle}
        description={copy.deleteText}
        open={deleting}
        onOpenChange={setDeleting}
        trigger={<Button variant="ghost">{copy.delete}</Button>}
        footer={
          <>
            <Button variant="ghost" onClick={() => setDeleting(false)}>
              {copy.cancel}
            </Button>
            <Button loading={remove.isPending} onClick={() => remove.mutate()}>
              {copy.delete}
            </Button>
          </>
        }
      />
    </>
  );
}
