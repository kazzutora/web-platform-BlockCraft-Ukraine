"use client";

import { useMutation } from "@tanstack/react-query";
import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { Icon } from "@/components/ui/Icon";
import { useToast } from "@/components/ui/useToast";
import { useRequireAuth } from "@/features/auth/useRequireAuth";
import { api } from "@/lib/api/client";

import { skinsCopy } from "./copy";

const copy = skinsCopy.detail;

/** «Зробити моїм скіном» / «Прибрати з профілю» (guests are asked to sign in). */
export function MakeMySkin({ skinId, initial }: { skinId: number; initial: boolean }) {
  const requireAuth = useRequireAuth();
  const toast = useToast();
  const [mine, setMine] = useState(initial);

  const change = useMutation({
    mutationFn: async (next: boolean) => {
      const { response } = next
        ? await api.PUT("/api/v1/me/skin", { body: { skin_id: skinId } })
        : await api.DELETE("/api/v1/me/skin");
      if (!response.ok) throw new Error(`/api/v1/me/skin: ${response.status}`);
      return next;
    },
    // Optimistic: the button flips at once and comes back if the request fails
    onMutate: (next) => setMine(next),
    onError: (_error, next) => {
      setMine(!next);
      toast({ title: copy.error, tone: "danger" });
    },
    onSuccess: (next) => toast({ title: next ? copy.madeMine : copy.clearedMine }),
  });

  if (mine) {
    return (
      <span className="inline-flex h-12 items-center gap-3 text-sm">
        <span className="inline-flex items-center gap-2 text-muted">
          <Icon name="check" />
          {copy.isMine}
        </span>
        <Button variant="ghost" onClick={() => change.mutate(false)}>
          {copy.clearMine}
        </Button>
      </span>
    );
  }
  return (
    <Button
      variant="secondary"
      size="lg"
      loading={change.isPending}
      onClick={() => requireAuth(() => change.mutate(true))}
    >
      <Icon name="user" />
      {copy.makeMine}
    </Button>
  );
}
