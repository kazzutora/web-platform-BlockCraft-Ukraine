"use client";

import { useMutation } from "@tanstack/react-query";
import { useId } from "react";

import { Button } from "@/components/ui/Button";
import { buttonClasses } from "@/components/ui/buttonClasses";
import { Icon } from "@/components/ui/Icon";
import { useToast } from "@/components/ui/useToast";
import { api } from "@/lib/api/client";
import { cn } from "@/lib/cn";

import { packsCopy } from "./copy";
import { PackCover } from "./PackCover";
import type { PackDetail } from "./types";

const copy = packsCopy.form.cover;

type CoverFieldProps = { pack: PackDetail; onChange: (pack: PackDetail) => void };

/** Optional cover; without it the pack shows the icons of its first mods. */
export function CoverField({ pack, onChange }: CoverFieldProps) {
  const toast = useToast();
  const inputId = useId();
  const hasCover = Boolean(pack.cover_url);

  const upload = useMutation({
    mutationFn: async (file: File) => {
      const { data } = await api.PUT("/api/v1/packs/{slug}/cover", {
        params: { path: { slug: pack.slug } },
        body: { cover: "" },
        bodySerializer: () => {
          const form = new FormData();
          form.append("cover", file);
          return form;
        },
      });
      if (!data) throw new Error("cover upload failed");
      return data;
    },
    onSuccess: onChange,
    onError: () => toast({ title: copy.error, tone: "danger" }),
  });
  const remove = useMutation({
    mutationFn: async () => {
      const { data } = await api.DELETE("/api/v1/packs/{slug}/cover", {
        params: { path: { slug: pack.slug } },
      });
      if (!data) throw new Error("cover delete failed");
      return data;
    },
    onSuccess: onChange,
    onError: () => toast({ title: copy.error, tone: "danger" }),
  });

  return (
    <section className="flex flex-col gap-3">
      <span className="text-sm font-medium" id={`${inputId}-label`}>
        {copy.label}
      </span>
      <div className="relative aspect-square w-40 border border-line bg-surface">
        <PackCover coverUrl={pack.cover_url} icons={pack.icons} />
      </div>
      <p className="text-meta text-muted">{copy.hint}</p>
      <div className="flex flex-wrap gap-3">
        <label
          className={cn(
            buttonClasses({ variant: "secondary" }),
            "cursor-pointer has-focus-visible:outline-2 has-focus-visible:outline-accent",
            upload.isPending && "pointer-events-none opacity-50",
          )}
        >
          <input
            type="file"
            accept="image/png,image/jpeg,image/webp"
            aria-labelledby={`${inputId}-label`}
            className="sr-only"
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) upload.mutate(file);
            }}
          />
          <Icon name="upload" />
          {copy.choose}
        </label>
        {hasCover && (
          <Button variant="ghost" loading={remove.isPending} onClick={() => remove.mutate()}>
            {copy.remove}
          </Button>
        )}
      </div>
    </section>
  );
}
