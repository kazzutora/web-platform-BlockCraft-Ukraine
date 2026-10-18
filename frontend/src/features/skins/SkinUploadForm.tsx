"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect, useId, useState } from "react";
import { Controller, useForm, useWatch } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/Button";
import { buttonClasses } from "@/components/ui/buttonClasses";
import { ChoiceChips } from "@/components/ui/ChoiceChips";
import { Icon } from "@/components/ui/Icon";
import { Input } from "@/components/ui/Input";
import { useToast } from "@/components/ui/useToast";
import { applyErrors } from "@/features/auth/applyErrors";
import { FormError } from "@/features/auth/FormError";
import { api } from "@/lib/api/client";
import { fieldErrors } from "@/lib/api/errors";
import { cn } from "@/lib/cn";
import { queryKeys } from "@/lib/query-keys";

import { skinsCopy } from "./copy";
import { SkinViewer } from "./SkinViewer";
import { inspectSkinFile } from "./texture";
import { MAX_STYLES, styles } from "./types";

const copy = skinsCopy.form;

const schema = z.object({
  title: z.string().trim().min(1, copy.errors.title).max(60, copy.errors.titleLong),
  model: z.enum(["classic", "slim"]),
  style_tags: z.array(z.enum(styles)).max(MAX_STYLES, copy.errors.styles),
});

type Values = z.infer<typeof schema>;
type Texture = { file: File; url: string };

/** /skins/new: PNG with checks in the browser, the skin in 3D before publishing. */
export function SkinUploadForm() {
  const router = useRouter();
  const toast = useToast();
  const queryClient = useQueryClient();
  const fileId = useId();
  const [texture, setTexture] = useState<Texture | null>(null);
  const [fileError, setFileError] = useState("");
  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { title: "", model: "classic", style_tags: [] },
  });
  const { errors, isSubmitting } = form.formState;
  const model = useWatch({ control: form.control, name: "model" });
  const title = useWatch({ control: form.control, name: "title" });

  useEffect(() => {
    if (!texture) return;
    return () => URL.revokeObjectURL(texture.url);
  }, [texture]);

  async function choose(file: File | undefined) {
    if (!file) return;
    const check = await inspectSkinFile(file);
    if (!check.ok) {
      setFileError(check.error);
      setTexture(null);
      return;
    }
    setFileError("");
    setTexture({ file, url: URL.createObjectURL(file) });
    form.setValue("model", check.model);
    if (!form.getValues("title")) {
      form.setValue("title", file.name.replace(/\.png$/i, "").slice(0, 60));
    }
  }

  async function onSubmit(values: Values) {
    if (!texture) {
      setFileError(copy.errors.file);
      return;
    }
    const { data, error } = await api.POST("/api/v1/skins", {
      body: { file: "", title: values.title, model: values.model, style_tags: values.style_tags },
      bodySerializer: () => {
        const body = new FormData();
        body.append("file", texture.file);
        body.append("title", values.title);
        body.append("model", values.model);
        for (const style of values.style_tags) body.append("style_tags", style);
        return body;
      },
    });
    if (!data) {
      const fileMessage = fieldErrors(error).file;
      if (fileMessage) setFileError(fileMessage);
      applyErrors(error, form.setError, ["title", "model", "style_tags"], copy.error);
      if (fileMessage) form.clearErrors("root");
      return;
    }
    toast({ title: data.status === "published" ? copy.published : copy.pending });
    await queryClient.invalidateQueries({ queryKey: queryKeys.skins.all });
    router.push(`/skins/${data.id}`);
  }

  return (
    <div className="grid gap-10 md:grid-cols-2 md:gap-16">
      <div className="flex flex-col gap-3">
        <div className="relative aspect-square border border-line bg-surface">
          {texture ? (
            <SkinViewer
              texture={texture.url}
              model={model}
              title={title || copy.title}
              poses={false}
            />
          ) : (
            <p className="flex size-full items-center justify-center p-8 text-center text-muted">
              {copy.noFile}
            </p>
          )}
        </div>
        {texture && <p className="text-meta text-muted">{copy.preview}</p>}
      </div>

      <form onSubmit={form.handleSubmit(onSubmit)} noValidate className="flex flex-col gap-6">
        <FormError message={errors.root?.message} />

        <div className="flex flex-col gap-2">
          <span className="text-sm font-medium" id={`${fileId}-label`}>
            {copy.file}
          </span>
          <div className="flex flex-wrap items-center gap-3">
            <label
              className={cn(
                buttonClasses({ variant: "secondary" }),
                "cursor-pointer has-focus-visible:outline-2 has-focus-visible:outline-accent",
              )}
            >
              <input
                id={fileId}
                type="file"
                accept="image/png"
                aria-labelledby={`${fileId}-label`}
                aria-describedby={`${fileId}-hint`}
                aria-invalid={fileError ? true : undefined}
                className="sr-only"
                onChange={(event) => void choose(event.target.files?.[0])}
              />
              <Icon name="upload" />
              {copy.chooseFile}
            </label>
            {texture && <span className="text-meta text-muted">{texture.file.name}</span>}
          </div>
          <p
            id={`${fileId}-hint`}
            className={cn("text-meta", fileError ? "text-danger" : "text-muted")}
          >
            {fileError || copy.fileHint}
          </p>
        </div>

        <Input
          label={copy.name}
          maxLength={60}
          error={errors.title?.message}
          {...form.register("title")}
        />

        <Controller
          control={form.control}
          name="model"
          render={({ field }) => (
            <div className="flex flex-col gap-2">
              <ChoiceChips
                label={copy.model}
                options={(["classic", "slim"] as const).map((value) => ({
                  value,
                  label: skinsCopy.models[value],
                }))}
                value={field.value}
                onChange={field.onChange}
                error={errors.model?.message}
              />
              {texture && <p className="text-meta text-muted">{copy.modelDetected}</p>}
            </div>
          )}
        />

        <Controller
          control={form.control}
          name="style_tags"
          render={({ field }) => (
            <div className="flex flex-col gap-2">
              <ChoiceChips
                multiple
                label={copy.styles}
                options={styles.map((value) => ({ value, label: skinsCopy.styles[value] }))}
                value={field.value}
                onChange={field.onChange}
                error={errors.style_tags?.message}
              />
              <p className="text-meta text-muted">{copy.stylesHint}</p>
            </div>
          )}
        />

        <Button type="submit" size="lg" loading={isSubmitting} className="self-start">
          {copy.submit}
        </Button>
      </form>
    </div>
  );
}
