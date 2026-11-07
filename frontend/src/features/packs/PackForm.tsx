"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Controller, useForm, useWatch } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/Button";
import { ChoiceChips } from "@/components/ui/ChoiceChips";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Textarea } from "@/components/ui/Textarea";
import { applyErrors } from "@/features/auth/applyErrors";
import { FormError } from "@/features/auth/FormError";
import { gameVersionOptions, gameVersions } from "@/features/game/labels";

import { packsCopy } from "./copy";
import { MAX_STYLES, type PackDetail, type PackWrite, packLoaders, packStyles } from "./types";

const copy = packsCopy.form;
const errors = copy.errors;

const schema = z.object({
  title: z.string().trim().min(1, errors.title).max(80),
  summary: z.string().trim().max(280),
  game_version: z.enum(gameVersions),
  loader: z.enum(packLoaders),
  style_tags: z.array(z.enum(packStyles)).max(MAX_STYLES),
  loader_version: z
    .string()
    .trim()
    .max(64)
    .regex(/^[\w.+-]*$/, errors.loaderVersion),
  ram_min_gb: z
    .string()
    .trim()
    .refine((value) => /^\d{1,2}$/.test(value) && Number(value) >= 1 && Number(value) <= 64, {
      error: errors.ram,
    }),
  gpu_note: z.string().trim().max(140),
  install_md: z.string().max(5000),
  changelog_md: z.string().max(5000),
});

type PackFormValues = z.infer<typeof schema>;

const FIELDS = Object.keys(schema.shape) as Array<keyof PackFormValues>;

export const emptyPack: PackFormValues = {
  title: "",
  summary: "",
  game_version: "1.21.1",
  loader: "fabric",
  style_tags: [],
  loader_version: "",
  ram_min_gb: "4",
  gpu_note: "",
  install_md: "",
  changelog_md: "",
};

export function valuesOf(pack: PackDetail): PackFormValues {
  return {
    title: pack.title,
    summary: pack.summary,
    game_version: pack.game_version,
    loader: pack.loader,
    style_tags: pack.style_tags,
    loader_version: pack.loader_version,
    ram_min_gb: String(pack.ram_min_gb),
    gpu_note: pack.gpu_note,
    install_md: pack.install_md,
    changelog_md: pack.changelog_md,
  };
}

type PackFormProps = {
  initial?: PackFormValues;
  /** Only what a new pack needs: title, target and a line about it. */
  short?: boolean;
  submitLabel: string;
  /** Resolves on success; rejects with the API error to show it on the fields. */
  onSubmit: (body: PackWrite) => Promise<unknown>;
};

export function PackForm({
  initial = emptyPack,
  short = false,
  submitLabel,
  onSubmit,
}: PackFormProps) {
  const form = useForm<PackFormValues>({ resolver: zodResolver(schema), defaultValues: initial });
  const { errors: fieldErrors, isSubmitting } = form.formState;
  const [gameVersion, loader] = useWatch({
    control: form.control,
    name: ["game_version", "loader"],
  });
  const saved = form.formState.defaultValues;
  const retargeting =
    !short && (gameVersion !== saved?.game_version || loader !== saved?.loader);

  async function submit(values: PackFormValues) {
    try {
      await onSubmit({ ...values, ram_min_gb: Number(values.ram_min_gb) });
      // What was saved is the new starting point (and hides the retarget hint)
      form.reset(values);
    } catch (error) {
      applyErrors(error, form.setError, FIELDS, copy.error);
    }
  }

  return (
    <form onSubmit={form.handleSubmit(submit)} noValidate className="flex flex-col gap-6">
      <FormError message={fieldErrors.root?.message} />
      <Input
        label={copy.title}
        maxLength={80}
        error={fieldErrors.title?.message}
        {...form.register("title")}
      />
      <Input
        label={copy.summary}
        hint={copy.summaryHint}
        maxLength={280}
        error={fieldErrors.summary?.message}
        {...form.register("summary")}
      />
      <Select
        label={copy.gameVersion}
        options={gameVersionOptions}
        error={fieldErrors.game_version?.message}
        {...form.register("game_version")}
      />
      <Controller
        control={form.control}
        name="loader"
        render={({ field }) => (
          <ChoiceChips
            label={copy.loader}
            options={packLoaders.map((value) => ({ value, label: packsCopy.loaders[value] }))}
            value={field.value}
            onChange={field.onChange}
            error={fieldErrors.loader?.message}
          />
        )}
      />
      {retargeting && (
        <p role="status" className="border border-line bg-surface p-4 text-sm">
          {copy.retarget}
        </p>
      )}
      {!short && (
        <>
          <Controller
            control={form.control}
            name="style_tags"
            render={({ field }) => (
              <div className="flex flex-col gap-2">
                <ChoiceChips
                  multiple
                  label={copy.styles}
                  options={packStyles.map((value) => ({ value, label: packsCopy.styles[value] }))}
                  value={field.value}
                  onChange={(next) => field.onChange(next.slice(0, MAX_STYLES))}
                  error={fieldErrors.style_tags?.message}
                />
                <p className="text-meta text-muted">{copy.stylesHint}</p>
              </div>
            )}
          />
          <div className="grid gap-6 sm:grid-cols-2">
            <Input
              label={copy.loaderVersion}
              hint={copy.loaderVersionHint}
              spellCheck={false}
              autoComplete="off"
              error={fieldErrors.loader_version?.message}
              {...form.register("loader_version")}
            />
            <Input
              label={copy.ram}
              inputMode="numeric"
              error={fieldErrors.ram_min_gb?.message}
              {...form.register("ram_min_gb")}
            />
          </div>
          <Input
            label={copy.gpu}
            hint={copy.gpuHint}
            maxLength={140}
            error={fieldErrors.gpu_note?.message}
            {...form.register("gpu_note")}
          />
          <Textarea
            label={copy.install}
            hint={copy.installHint}
            rows={6}
            maxLength={5000}
            error={fieldErrors.install_md?.message}
            {...form.register("install_md")}
          />
          <Textarea
            label={copy.changelog}
            hint={copy.changelogHint}
            rows={4}
            maxLength={5000}
            error={fieldErrors.changelog_md?.message}
            {...form.register("changelog_md")}
          />
        </>
      )}
      <Button type="submit" size="lg" loading={isSubmitting} className="self-start">
        {submitLabel}
      </Button>
    </form>
  );
}
