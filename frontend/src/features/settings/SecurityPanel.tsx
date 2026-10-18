"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";

import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { useToast } from "@/components/ui/useToast";
import { applyErrors } from "@/features/auth/applyErrors";
import { authCopy } from "@/features/auth/copy";
import { FormError } from "@/features/auth/FormError";
import { type ChangePasswordValues, changePasswordSchema } from "@/features/auth/schemas";
import type { Me } from "@/features/auth/useMe";
import { auth } from "@/lib/api/auth-client";

import { settingsCopy } from "./copy";

const copy = settingsCopy.security;

export function SecurityPanel({ me }: { me: Me }) {
  const toast = useToast();
  const form = useForm<ChangePasswordValues>({
    resolver: zodResolver(changePasswordSchema),
    defaultValues: { current_password: "", new_password: "" },
  });
  const { errors, isSubmitting } = form.formState;

  async function onSubmit(values: ChangePasswordValues) {
    const { error, response } = await auth.POST("/_allauth/browser/v1/account/password/change", {
      body: values,
    });
    if (response.ok) {
      form.reset();
      toast({ title: copy.changed });
      return;
    }
    applyErrors(
      error,
      form.setError,
      ["current_password", "new_password"],
      authCopy.errors.generic,
    );
  }

  return (
    <div className="flex max-w-xl flex-col gap-10">
      <Input label={copy.email} value={me.email} disabled readOnly />
      <form onSubmit={form.handleSubmit(onSubmit)} noValidate className="flex flex-col gap-6">
        <h2 className="text-h2">{copy.changePassword}</h2>
        <FormError message={errors.root?.message} />
        <Input
          label={authCopy.fields.currentPassword}
          type="password"
          autoComplete="current-password"
          error={errors.current_password?.message}
          {...form.register("current_password")}
        />
        <Input
          label={authCopy.fields.newPassword}
          type="password"
          autoComplete="new-password"
          hint={authCopy.fields.passwordHint}
          error={errors.new_password?.message}
          {...form.register("new_password")}
        />
        <Button type="submit" className="self-start" loading={isSubmitting}>
          {copy.submit}
        </Button>
      </form>
    </div>
  );
}
