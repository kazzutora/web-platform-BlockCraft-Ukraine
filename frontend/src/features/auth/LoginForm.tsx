"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";

import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { auth } from "@/lib/api/auth-client";

import { applyErrors } from "./applyErrors";
import { authCopy } from "./copy";
import { pendingFlow } from "./flows";
import { FormError } from "./FormError";
import { type LoginValues, loginSchema } from "./schemas";
import { SocialButtons } from "./SocialButtons";
import { useSignedIn } from "./useSignedIn";

const copy = authCopy.login;

export function LoginForm() {
  const searchParams = useSearchParams();
  const next = searchParams.get("next");
  const signedIn = useSignedIn();
  const [unverified, setUnverified] = useState(false);
  const [resent, setResent] = useState(false);
  const form = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "" },
  });
  const { errors, isSubmitting } = form.formState;

  async function onSubmit(values: LoginValues) {
    setUnverified(false);
    const { error, response } = await auth.POST("/_allauth/browser/v1/auth/login", {
      body: values,
    });
    if (response.ok) {
      await signedIn(next);
      return;
    }
    if (response.status === 401 && pendingFlow(error) === "verify_email") {
      setUnverified(true);
      return;
    }
    applyErrors(error, form.setError, ["email", "password"], authCopy.errors.generic);
  }

  async function resend() {
    await auth.POST("/_allauth/browser/v1/auth/email/verify/resend");
    setResent(true);
  }

  return (
    <div className="flex flex-col gap-8">
      {searchParams.get("error") === "social" && <FormError message={copy.socialError} />}
      <form onSubmit={form.handleSubmit(onSubmit)} noValidate className="flex flex-col gap-6">
        <FormError message={errors.root?.message} />
        {unverified && (
          <div role="status" className="flex flex-col gap-3 border border-text p-4 text-sm">
            <p>{copy.unverified}</p>
            {resent ? (
              <p className="text-muted">{copy.resent}</p>
            ) : (
              <Button variant="ghost" className="self-start px-0" onClick={resend}>
                {copy.resend}
              </Button>
            )}
          </div>
        )}
        <Input
          label={authCopy.fields.email}
          type="email"
          autoComplete="email"
          error={errors.email?.message}
          {...form.register("email")}
        />
        <Input
          label={authCopy.fields.password}
          type="password"
          autoComplete="current-password"
          error={errors.password?.message}
          {...form.register("password")}
        />
        <Link
          href="/password-reset"
          className="-mt-2 self-start text-sm underline underline-offset-4"
        >
          {copy.forgot}
        </Link>
        <Button type="submit" size="lg" loading={isSubmitting}>
          {copy.submit}
        </Button>
      </form>
      <SocialButtons next={next} />
      <p className="text-sm text-muted">
        {copy.noAccount}{" "}
        <Link
          href={next ? `/register?next=${encodeURIComponent(next)}` : "/register"}
          className="text-text underline underline-offset-4"
        >
          {copy.register}
        </Link>
      </p>
    </div>
  );
}
