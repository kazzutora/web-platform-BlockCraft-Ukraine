"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useQueryClient } from "@tanstack/react-query";
import { useRouter, useSearchParams } from "next/navigation";
import { Controller, useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/Button";
import { ChoiceChips } from "@/components/ui/ChoiceChips";
import { Input } from "@/components/ui/Input";
import { useToast } from "@/components/ui/useToast";
import { applyErrors } from "@/features/auth/applyErrors";
import { FormError } from "@/features/auth/FormError";
import { api } from "@/lib/api/client";
import { queryKeys } from "@/lib/query-keys";

import { serversCopy } from "./copy";
import type { ServerEdition } from "./types";

const copy = serversCopy.addForm;
const editions: ServerEdition[] = ["java", "bedrock"];

const schema = z.object({
  address: z.string().trim().min(1, copy.required).max(260),
  edition: z.enum(editions),
});

type Values = z.infer<typeof schema>;

/**
 * /servers/add — «Мій сервер»: the address must answer a ping; then the server page shows
 * the code for the MOTD. A server already in the catalog (from Modrinth) is claimed the
 * same way (`?address=` comes from its page).
 */
export function AddServer() {
  const router = useRouter();
  const toast = useToast();
  const queryClient = useQueryClient();
  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { address: useSearchParams().get("address") ?? "", edition: "java" },
  });
  const { errors, isSubmitting } = form.formState;

  async function submit(values: Values) {
    const { data, error } = await api.POST("/api/v1/servers", { body: values });
    if (!data) {
      applyErrors(error, form.setError, ["address", "edition"], copy.error);
      return;
    }
    toast({ title: copy.done });
    await queryClient.invalidateQueries({ queryKey: queryKeys.servers.all });
    router.push(`/servers/${data.slug}`);
  }

  return (
    <form onSubmit={form.handleSubmit(submit)} noValidate className="flex flex-col gap-6">
      <FormError message={errors.root?.message} />
      <Input
        label={copy.address}
        hint={copy.addressHint}
        autoComplete="off"
        spellCheck={false}
        placeholder="play.example.com"
        error={errors.address?.message}
        {...form.register("address")}
      />
      <Controller
        control={form.control}
        name="edition"
        render={({ field }) => (
          <ChoiceChips
            label={copy.edition}
            options={editions.map((value) => ({ value, label: serversCopy.editions[value] }))}
            value={field.value}
            onChange={field.onChange}
            error={errors.edition?.message}
          />
        )}
      />
      <Button type="submit" size="lg" loading={isSubmitting} className="self-start">
        {copy.submit}
      </Button>
    </form>
  );
}
