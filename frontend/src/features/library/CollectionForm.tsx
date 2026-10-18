"use client";

import { type FormEvent, useState } from "react";

import { Button } from "@/components/ui/Button";
import { ChoiceChips } from "@/components/ui/ChoiceChips";
import { Input } from "@/components/ui/Input";
import { Textarea } from "@/components/ui/Textarea";
import { FormError } from "@/features/auth/FormError";
import { fieldErrors } from "@/lib/api/errors";

import { libraryCopy } from "./copy";
import type { Visibility } from "./types";

const copy = libraryCopy.form;
const visibilities: Visibility[] = ["private", "link", "public"];

export type CollectionFormValues = {
  title: string;
  description: string;
  visibility: Visibility;
  editors?: string;
};

type CollectionFormProps = {
  initial?: Partial<CollectionFormValues>;
  /** Owners also manage editors. */
  withEditors?: boolean;
  submitLabel: string;
  onSubmit: (values: CollectionFormValues) => Promise<unknown>;
};

/** Title, description, visibility (and editors for the owner); API errors land on fields. */
export function CollectionForm({
  initial,
  withEditors = false,
  submitLabel,
  onSubmit,
}: CollectionFormProps) {
  const [values, setValues] = useState<CollectionFormValues>({
    title: initial?.title ?? "",
    description: initial?.description ?? "",
    visibility: initial?.visibility ?? "private",
    editors: initial?.editors ?? "",
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!values.title.trim()) {
      setErrors({ title: copy.titleRequired });
      return;
    }
    setBusy(true);
    setErrors({});
    try {
      await onSubmit(values);
    } catch (error) {
      const fields = fieldErrors(error);
      setErrors(Object.keys(fields).length ? fields : { root: copy.error });
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} noValidate className="flex flex-col gap-6">
      <FormError message={errors.root} />
      <Input
        label={copy.title}
        maxLength={80}
        required
        value={values.title}
        onChange={(event) => setValues({ ...values, title: event.target.value })}
        error={errors.title}
      />
      <Textarea
        label={copy.description}
        hint={copy.descriptionHint}
        maxLength={200}
        rows={2}
        value={values.description}
        onChange={(event) => setValues({ ...values, description: event.target.value })}
        error={errors.description}
      />
      <div className="flex flex-col gap-2">
        <ChoiceChips
          label={copy.visibility}
          options={visibilities.map((value) => ({ value, label: libraryCopy.visibility[value] }))}
          value={values.visibility}
          onChange={(visibility) => setValues({ ...values, visibility })}
        />
        <p className="text-meta text-muted">{libraryCopy.visibilityHint[values.visibility]}</p>
      </div>
      {withEditors && (
        <Input
          label={copy.editors}
          hint={copy.editorsHint}
          value={values.editors}
          onChange={(event) => setValues({ ...values, editors: event.target.value })}
          error={errors.editors}
        />
      )}
      <Button type="submit" size="lg" loading={busy} className="self-start">
        {submitLabel}
      </Button>
    </form>
  );
}

export function parseEditors(value = ""): string[] {
  return value
    .split(/[\s,]+/)
    .map((nickname) => nickname.trim())
    .filter(Boolean);
}
