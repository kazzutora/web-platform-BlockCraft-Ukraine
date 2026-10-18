"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Controller, useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/Button";
import { Checkbox } from "@/components/ui/Checkbox";
import { ChoiceChips } from "@/components/ui/ChoiceChips";
import { Input } from "@/components/ui/Input";
import { Textarea } from "@/components/ui/Textarea";
import { applyErrors } from "@/features/auth/applyErrors";
import { FormError } from "@/features/auth/FormError";

import { serversCopy } from "./copy";
import { MAX_MODES, type ServerWrite, editions, languages, modes } from "./types";

const copy = serversCopy.form;
const errors = copy.errors;
const optionalUrl = z.union([z.literal(""), z.url({ protocol: /^https?$/, error: errors.url })]);

const schema = z.object({
  name: z.string().trim().min(1, errors.name).max(60),
  host: z.string().trim().min(1, errors.host).max(260),
  port: z
    .string()
    .trim()
    .refine((value) => value === "" || /^\d{1,5}$/.test(value), errors.port)
    .refine((value) => value === "" || (Number(value) >= 1 && Number(value) <= 65535), errors.port),
  edition: z.enum(editions),
  modes: z.array(z.enum(modes)).min(1, errors.modes).max(MAX_MODES, errors.modes),
  versions_label: z.string().trim().max(32),
  language: z.enum(languages),
  description: z.string().trim().max(500),
  discord_url: optionalUrl,
  website_url: optionalUrl,
  has_whitelist: z.boolean(),
});

export type ServerFormValues = z.infer<typeof schema>;

const FIELDS = [
  "name",
  "host",
  "port",
  "edition",
  "modes",
  "versions_label",
  "language",
  "description",
  "discord_url",
  "website_url",
  "has_whitelist",
] as const;

export const emptyServer: ServerFormValues = {
  name: "",
  host: "",
  port: "",
  edition: "java",
  modes: [],
  versions_label: "",
  language: "uk",
  description: "",
  discord_url: "",
  website_url: "",
  has_whitelist: false,
};

export function toRequest(values: ServerFormValues): ServerWrite {
  return { ...values, port: values.port ? Number(values.port) : null };
}

type ServerFormProps = {
  initial?: ServerFormValues;
  submitLabel: string;
  /** Resolves on success; rejects with the API error to show it on the fields. */
  onSubmit: (body: ServerWrite) => Promise<unknown>;
};

/** Add or edit a server: address, edition, modes, language and links. */
export function ServerForm({ initial = emptyServer, submitLabel, onSubmit }: ServerFormProps) {
  const form = useForm<ServerFormValues>({ resolver: zodResolver(schema), defaultValues: initial });
  const { errors: fieldErrors, isSubmitting } = form.formState;

  async function submit(values: ServerFormValues) {
    try {
      await onSubmit(toRequest(values));
    } catch (error) {
      applyErrors(error, form.setError, [...FIELDS], copy.error);
    }
  }

  return (
    <form onSubmit={form.handleSubmit(submit)} noValidate className="flex flex-col gap-6">
      <FormError message={fieldErrors.root?.message} />
      <Input
        label={copy.name}
        maxLength={60}
        error={fieldErrors.name?.message}
        {...form.register("name")}
      />
      <div className="grid gap-6 sm:grid-cols-[minmax(0,1fr)_10rem]">
        <Input
          label={copy.host}
          hint={copy.hostHint}
          autoComplete="off"
          spellCheck={false}
          error={fieldErrors.host?.message}
          {...form.register("host")}
        />
        <Input
          label={copy.port}
          hint={copy.portHint}
          inputMode="numeric"
          error={fieldErrors.port?.message}
          {...form.register("port")}
        />
      </div>
      <Controller
        control={form.control}
        name="edition"
        render={({ field }) => (
          <ChoiceChips
            label={copy.edition}
            options={editions.map((value) => ({ value, label: serversCopy.editions[value] }))}
            value={field.value}
            onChange={field.onChange}
            error={fieldErrors.edition?.message}
          />
        )}
      />
      <Controller
        control={form.control}
        name="modes"
        render={({ field }) => (
          <div className="flex flex-col gap-2">
            <ChoiceChips
              multiple
              label={copy.modes}
              options={modes.map((value) => ({ value, label: serversCopy.modes[value] }))}
              value={field.value}
              onChange={field.onChange}
              error={fieldErrors.modes?.message}
            />
            <p className="text-meta text-muted">{copy.modesHint}</p>
          </div>
        )}
      />
      <Input
        label={copy.versions}
        hint={copy.versionsHint}
        maxLength={32}
        error={fieldErrors.versions_label?.message}
        {...form.register("versions_label")}
      />
      <Controller
        control={form.control}
        name="language"
        render={({ field }) => (
          <ChoiceChips
            label={copy.language}
            options={languages.map((value) => ({ value, label: serversCopy.languages[value] }))}
            value={field.value}
            onChange={field.onChange}
            error={fieldErrors.language?.message}
          />
        )}
      />
      <Textarea
        label={copy.description}
        hint={copy.descriptionHint}
        maxLength={500}
        rows={4}
        error={fieldErrors.description?.message}
        {...form.register("description")}
      />
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
      <Checkbox label={copy.whitelist} {...form.register("has_whitelist")} />
      <Button type="submit" size="lg" loading={isSubmitting} className="self-start">
        {submitLabel}
      </Button>
    </form>
  );
}
