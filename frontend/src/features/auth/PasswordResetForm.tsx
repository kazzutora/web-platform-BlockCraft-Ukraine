"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";

import { Button } from "@/components/ui/Button";
import { ButtonLink } from "@/components/ui/ButtonLink";
import { Input } from "@/components/ui/Input";
import { auth } from "@/lib/api/auth-client";
import { fieldErrors } from "@/lib/api/errors";

import { applyErrors } from "./applyErrors";
import { authCopy } from "./copy";
import { FormError } from "./FormError";
import { type ResetPasswordValues, resetPasswordSchema } from "./schemas";
import { useSignedIn } from "./useSignedIn";

const copy = authCopy.reset;

/** New password from the emailed link. */
export function PasswordResetForm({ resetKey }: { resetKey: string }) {
  const signedIn = useSignedIn();
  const [state, setState] = useState<"form" | "done" | "invalid">("form");
  const form = useForm<ResetPasswordValues>({
    resolver: zodResolver(resetPasswordSchema),
    defaultValues: { password: "" },
  });
  const { errors, isSubmitting } = form.formState;

  async function onSubmit(values: ResetPasswordValues) {
    const { error, response } = await auth.POST("/_allauth/browser/v1/auth/password/reset", {
      body: { key: resetKey, password: values.password },
    });
    if (response.ok) {
      await signedIn("/");
      return;
    }
    // 401: the password is changed, the user signs in on their own
    if (response.status === 401) {
      setState("done");
      return;
    }
    if (fieldErrors(error).key) {
      setState("invalid");
      return;
    }
    applyErrors(error, form.setError, ["password"], authCopy.errors.generic);
  }

  if (state !== "form") {
    return (
      <div role="status" className="flex flex-col items-start gap-6">
        <p>{state === "done" ? copy.done : copy.invalid}</p>
        <ButtonLink href={state === "done" ? "/login" : "/password-reset"} size="lg">
          {state === "done" ? authCopy.login.submit : copy.requestAgain}
        </ButtonLink>
      </div>
    );
  }

  return (
    <form onSubmit={form.handleSubmit(onSubmit)} noValidate className="flex flex-col gap-6">
      <FormError message={errors.root?.message} />
      <Input
        label={authCopy.fields.newPassword}
        type="password"
        autoComplete="new-password"
        hint={authCopy.fields.passwordHint}
        error={errors.password?.message}
        {...form.register("password")}
      />
      <Button type="submit" size="lg" loading={isSubmitting}>
        {copy.newSubmit}
      </Button>
    </form>
  );
}
