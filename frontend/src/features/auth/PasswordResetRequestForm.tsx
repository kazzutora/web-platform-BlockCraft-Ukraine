"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";

import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { auth } from "@/lib/api/auth-client";

import { applyErrors } from "./applyErrors";
import { authCopy } from "./copy";
import { FormError } from "./FormError";
import { type ResetRequestValues, resetRequestSchema } from "./schemas";

const copy = authCopy.reset;

export function PasswordResetRequestForm() {
  const [sent, setSent] = useState(false);
  const form = useForm<ResetRequestValues>({
    resolver: zodResolver(resetRequestSchema),
    defaultValues: { email: "" },
  });
  const { errors, isSubmitting } = form.formState;

  async function onSubmit(values: ResetRequestValues) {
    const { error, response } = await auth.POST("/_allauth/browser/v1/auth/password/request", {
      body: values,
    });
    if (response.ok) {
      setSent(true);
      return;
    }
    applyErrors(error, form.setError, ["email"], authCopy.errors.generic);
  }

  if (sent) {
    return (
      <p role="status" className="border border-text p-4">
        {copy.sent}
      </p>
    );
  }

  return (
    <form onSubmit={form.handleSubmit(onSubmit)} noValidate className="flex flex-col gap-6">
      <FormError message={errors.root?.message} />
      <Input
        label={authCopy.fields.email}
        type="email"
        autoComplete="email"
        error={errors.email?.message}
        {...form.register("email")}
      />
      <Button type="submit" size="lg" loading={isSubmitting}>
        {copy.submit}
      </Button>
    </form>
  );
}
