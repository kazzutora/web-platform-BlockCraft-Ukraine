"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import Image from "next/image";
import { useRouter } from "next/navigation";
import { useId, useState } from "react";

import { Button } from "@/components/ui/Button";
import { buttonClasses } from "@/components/ui/buttonClasses";
import { Icon } from "@/components/ui/Icon";
import { useToast } from "@/components/ui/useToast";
import { api } from "@/lib/api/client";
import { cn } from "@/lib/cn";
import { queryKeys } from "@/lib/query-keys";

import { serversCopy } from "./copy";
import { ServerForm } from "./ServerForm";
import type { ServerDetail } from "./types";

const copy = serversCopy.form;

/** /servers/[slug]/edit: the same form plus the banner. */
export function EditServer({ server }: { server: ServerDetail }) {
  const router = useRouter();
  const toast = useToast();
  const queryClient = useQueryClient();

  return (
    <div className="flex flex-col gap-12">
      <BannerField slug={server.slug} initialUrl={server.banner_url} />
      <ServerForm
        submitLabel={copy.submitEdit}
        initial={{
          name: server.name,
          host: server.host,
          port: String(server.port),
          edition: server.edition,
          modes: server.modes,
          versions_label: server.versions_label,
          language: server.language,
          description: server.description,
          discord_url: server.discord_url,
          website_url: server.website_url,
          has_whitelist: server.has_whitelist,
        }}
        onSubmit={async (body) => {
          const { data, error } = await api.PATCH("/api/v1/servers/{slug}", {
            params: { path: { slug: server.slug } },
            body,
          });
          if (!data) throw error;
          toast({ title: copy.saved });
          await queryClient.invalidateQueries({ queryKey: queryKeys.servers.all });
          router.push(`/servers/${data.slug}`);
          router.refresh();
        }}
      />
    </div>
  );
}

function BannerField({ slug, initialUrl }: { slug: string; initialUrl: string | null }) {
  const toast = useToast();
  const inputId = useId();
  const [url, setUrl] = useState(initialUrl);
  const copyBanner = serversCopy.banner;

  const upload = useMutation({
    mutationFn: async (file: File) => {
      const { data } = await api.PUT("/api/v1/servers/{slug}/banner", {
        params: { path: { slug } },
        body: { banner: "" },
        bodySerializer: () => {
          const form = new FormData();
          form.append("banner", file);
          return form;
        },
      });
      if (!data) throw new Error("banner upload failed");
      return data;
    },
    onSuccess: (data) => setUrl(data.banner_url),
    onError: () => toast({ title: copyBanner.error, tone: "danger" }),
  });
  const remove = useMutation({
    mutationFn: async () => {
      const { data } = await api.DELETE("/api/v1/servers/{slug}/banner", {
        params: { path: { slug } },
      });
      if (!data) throw new Error("banner delete failed");
      return data;
    },
    onSuccess: () => setUrl(null),
    onError: () => toast({ title: copyBanner.error, tone: "danger" }),
  });

  return (
    <section className="flex flex-col gap-3">
      <span className="text-sm font-medium" id={`${inputId}-label`}>
        {copyBanner.label}
      </span>
      <div className="aspect-[4/1] w-full border border-line bg-surface">
        {url && (
          <Image
            src={url}
            alt=""
            width={1200}
            height={300}
            unoptimized
            className="size-full object-cover"
          />
        )}
      </div>
      <p className="text-meta text-muted">{copyBanner.hint}</p>
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
          {copyBanner.choose}
        </label>
        {url && (
          <Button variant="ghost" loading={remove.isPending} onClick={() => remove.mutate()}>
            {copyBanner.remove}
          </Button>
        )}
      </div>
    </section>
  );
}
