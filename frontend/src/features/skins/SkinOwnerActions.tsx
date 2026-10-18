"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { Icon } from "@/components/ui/Icon";
import { useToast } from "@/components/ui/useToast";
import { api } from "@/lib/api/client";
import { queryKeys } from "@/lib/query-keys";

import { skinsCopy } from "./copy";
import type { SkinDetail } from "./types";

const copy = skinsCopy.detail;

/** For the author: show the skin in the profile, delete it. */
export function SkinOwnerActions({ skin }: { skin: SkinDetail }) {
  const queryClient = useQueryClient();
  const router = useRouter();
  const toast = useToast();
  const [current, setCurrent] = useState(skin.is_current);
  const [deleting, setDeleting] = useState(false);

  const makeCurrent = useMutation({
    mutationFn: async () => {
      const { data } = await api.PUT("/api/v1/me/skin", { body: { skin_id: skin.id } });
      if (!data) throw new Error("PUT /api/v1/me/skin failed");
      return data;
    },
    onMutate: () => setCurrent(true),
    onError: () => {
      setCurrent(false);
      toast({ title: copy.error, tone: "danger" });
    },
    onSuccess: () => {
      toast({ title: copy.madeCurrent });
      void queryClient.invalidateQueries({ queryKey: queryKeys.skins.all });
    },
  });

  const remove = useMutation({
    mutationFn: async () => {
      const { response } = await api.DELETE("/api/v1/skins/{id}", {
        params: { path: { id: skin.id } },
      });
      if (!response.ok) throw new Error(`DELETE /api/v1/skins/${skin.id}: ${response.status}`);
    },
    onError: () => toast({ title: copy.error, tone: "danger" }),
    onSuccess: async () => {
      toast({ title: copy.deleted });
      await queryClient.invalidateQueries({ queryKey: queryKeys.skins.all });
      router.push("/me/works");
    },
  });

  const canBeCurrent = skin.status === "published" || skin.status === "pending";

  return (
    <>
      {canBeCurrent &&
        (current ? (
          <span className="inline-flex h-12 items-center gap-2 text-sm text-muted">
            <Icon name="user" size={16} />
            {copy.isCurrent}
          </span>
        ) : (
          <Button
            variant="secondary"
            size="lg"
            loading={makeCurrent.isPending}
            onClick={() => makeCurrent.mutate()}
          >
            <Icon name="user" />
            {copy.makeCurrent}
          </Button>
        ))}
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
