"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { Controller, useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/Button";
import { ChoiceChips } from "@/components/ui/ChoiceChips";
import { Input } from "@/components/ui/Input";
import { Textarea } from "@/components/ui/Textarea";
import { useToast } from "@/components/ui/useToast";
import { applyErrors } from "@/features/auth/applyErrors";
import { FormError } from "@/features/auth/FormError";
import { useMe } from "@/features/auth/useMe";
import { api } from "@/lib/api/client";
import { queryKeys } from "@/lib/query-keys";

import { serversCopy } from "./copy";
import { type ServerDetail, type ServerWrite, contentKinds } from "./types";

const copy = serversCopy.form;
const errors = copy.errors;
const optionalUrl = z.union([z.literal(""), z.url({ protocol: /^https?$/, error: errors.url })]);
const list = (value: string) =>
  value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);

const schema = z.object({
  name: z.string().trim().min(1).max(80),
  summary: z.string().trim().max(280),
  description_uk_md: z.string().trim().max(5000),
  discord_url: optionalUrl,
  website_url: optionalUrl,
  required_pack: z.string().trim().max(96),
  languages: z
    .string()
    .refine((value) => list(value).every((code) => /^[a-z]{2}$/.test(code)), errors.languages),
  country: z
    .string()
    .trim()
    .regex(/^([A-Za-z]{2})?$/, errors.country),
  content_kind: z.enum(contentKinds),
  supported_versions: z.string().max(400),
  recommended_version: z.string().trim().max(32),
});

type Values = z.infer<typeof schema>;

/** Owner fields for every server; a server added here also has its facts editable. */
const OWNER_FIELDS = [
  "summary",
  "description_uk_md",
  "discord_url",
  "website_url",
  "required_pack",
] as const;
const OWN_FIELDS = [
  "name",
  "languages",
  "country",
  "content_kind",
  "supported_versions",
  "recommended_version",
] as const;

function toRequest(values: Values, own: boolean): ServerWrite {
  const body: ServerWrite = {
    summary: values.summary,
    description_uk_md: values.description_uk_md,
    discord_url: values.discord_url,
    website_url: values.website_url,
    required_pack: values.required_pack,
  };
  if (!own) return body;
  return {
    ...body,
    name: values.name,
    languages: list(values.languages),
    country: values.country.toUpperCase(),
    content_kind: values.content_kind,
    supported_versions: list(values.supported_versions),
    recommended_version: values.recommended_version,
  };
}

/** /servers/[slug]/edit: what the proven owner writes here, in Ukrainian. */
export function EditServer({ server }: { server: ServerDetail }) {
  const router = useRouter();
  const toast = useToast();
  const queryClient = useQueryClient();
  // Facts of a Modrinth server are edited on Modrinth and come back with the sync
  const own = server.source === null;
  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: server.name,
      summary: server.summary,
      description_uk_md: server.description_uk_md,
      discord_url: server.discord_url,
      website_url: server.website_url,
      required_pack: server.required_pack?.slug ?? "",
      languages: server.languages.join(", "),
      country: server.country,
      content_kind: server.content_kind,
      supported_versions: server.supported_versions.join(", "),
      recommended_version: server.recommended_version,
    },
  });
  const fieldErrors = form.formState.errors;
  const myPacks = useMyPublicPacks();

  async function submit(values: Values) {
    const { data, error } = await api.PATCH("/api/v1/servers/{slug}", {
      params: { path: { slug: server.slug } },
      body: toRequest(values, own),
    });
    if (!data) {
      applyErrors(error, form.setError, [...OWNER_FIELDS, ...OWN_FIELDS], copy.error);
      return;
    }
    toast({ title: copy.saved });
    await queryClient.invalidateQueries({ queryKey: queryKeys.servers.all });
    router.push(`/servers/${data.slug}`);
    router.refresh();
  }

  return (
    <form onSubmit={form.handleSubmit(submit)} noValidate className="flex flex-col gap-6">
      <FormError message={fieldErrors.root?.message} />
      {own ? (
        <>
          <Input
            label={copy.name}
            maxLength={80}
            error={fieldErrors.name?.message}
            {...form.register("name")}
          />
          <div className="grid gap-6 sm:grid-cols-2">
            <Input
              label={copy.languages}
              hint={copy.languagesHint}
              error={fieldErrors.languages?.message}
              {...form.register("languages")}
            />
            <Input
              label={copy.country}
              hint={copy.countryHint}
              maxLength={2}
              error={fieldErrors.country?.message}
              {...form.register("country")}
            />
          </div>
          <Controller
            control={form.control}
            name="content_kind"
            render={({ field }) => (
              <ChoiceChips
                label={copy.kind}
                options={contentKinds.map((value) => ({
                  value,
                  label: serversCopy.kinds[value],
                }))}
                value={field.value}
                onChange={field.onChange}
              />
            )}
          />
          <div className="grid gap-6 sm:grid-cols-2">
            <Input
              label={copy.versions}
              hint={copy.versionsHint}
              error={fieldErrors.supported_versions?.message}
              {...form.register("supported_versions")}
            />
            <Input
              label={copy.recommended}
              maxLength={32}
              error={fieldErrors.recommended_version?.message}
              {...form.register("recommended_version")}
            />
          </div>
        </>
      ) : (
        <p className="max-w-prose border border-line p-4 text-sm text-muted">{copy.fromSource}</p>
      )}
      <Textarea
        label={copy.summary}
        hint={copy.summaryHint}
        maxLength={280}
        rows={2}
        error={fieldErrors.summary?.message}
        {...form.register("summary")}
      />
      <Textarea
        label={copy.description}
        hint={copy.descriptionHint}
        maxLength={5000}
        rows={10}
        error={fieldErrors.description_uk_md?.message}
        {...form.register("description_uk_md")}
      />
      <Input
        label={copy.pack}
        hint={copy.packHint}
        autoComplete="off"
        spellCheck={false}
        list="my-packs"
        error={fieldErrors.required_pack?.message}
        {...form.register("required_pack")}
      />
      <datalist id="my-packs">
        {myPacks.map((pack) => (
          <option key={pack.slug} value={pack.slug}>
            {pack.title}
          </option>
        ))}
      </datalist>
      <div className="grid gap-6 sm:grid-cols-2">
        <Input
          label={copy.discord}
          type="url"
          placeholder="https://discord.gg/…"
          error={fieldErrors.discord_url?.message}
          {...form.register("discord_url")}
        />
        <Input
          label={copy.website}
          type="url"
          placeholder="https://"
          error={fieldErrors.website_url?.message}
          {...form.register("website_url")}
        />
      </div>
      <Button type="submit" size="lg" loading={form.formState.isSubmitting} className="self-start">
        {copy.submit}
      </Button>
    </form>
  );
}

/** Suggestions for «Збірка для входу»: my packs anyone can take (published, «усім»). */
function useMyPublicPacks() {
  const { me } = useMe();
  const nickname = me?.nickname ?? "";
  const packs = useQuery({
    queryKey: queryKeys.packs.catalog({ author: nickname, all: true, page_size: 60 }),
    enabled: Boolean(nickname),
    queryFn: async () => {
      const { data } = await api.GET("/api/v1/packs", {
        params: { query: { author: nickname, all: true, page_size: 60 } },
      });
      return data?.results ?? [];
    },
  });
  return packs.data ?? [];
}
