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
import { useGameVersions } from "@/features/game/useGameVersions";

import { packsCopy } from "./copy";
import { type PackDetail, type PackWrite, packLoaders } from "./types";

const copy = packsCopy.form;
const errors = copy.errors;

const schema = z.object({
  title: z.string().trim().min(1, errors.title).max(80),
  summary: z.string().trim().max(280),
  game_version: z.string().min(1, errors.gameVersion),
  loader: z.enum(packLoaders),
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
  notes_md: z.string().max(5000),
});

type PackFormValues = z.infer<typeof schema>;

const FIELDS = Object.keys(schema.shape) as Array<keyof PackFormValues>;

export const emptyPack: PackFormValues = {
  title: "",
  summary: "",
  game_version: "",
  loader: "fabric",
  loader_version: "",
  ram_min_gb: "4",
  notes_md: "",
};

export function valuesOf(pack: PackDetail): PackFormValues {
  return {
    title: pack.title,
    summary: pack.summary,
    game_version: pack.game_version,
    loader: pack.loader,
    loader_version: pack.loader_version,
    ram_min_gb: String(pack.ram_min_gb),
    notes_md: pack.notes_md,
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
  const supported = useGameVersions();
  // A pack made for a version that is no longer supported keeps it in the list
  const versionOptions = [
    ...(saved?.game_version && !supported.includes(saved.game_version) ? [saved.game_version] : []),
    ...supported,
  ].map((version) => ({ value: version, label: version }));
  const retargeting = !short && (gameVersion !== saved?.game_version || loader !== saved?.loader);

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
        options={versionOptions}
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
          <Textarea
            label={copy.notes}
            hint={copy.notesHint}
            rows={6}
            maxLength={5000}
            error={fieldErrors.notes_md?.message}
            {...form.register("notes_md")}
          />
        </>
      )}
      <Button type="submit" size="lg" loading={isSubmitting} className="self-start">
        {submitLabel}
      </Button>
    </form>
  );
}
