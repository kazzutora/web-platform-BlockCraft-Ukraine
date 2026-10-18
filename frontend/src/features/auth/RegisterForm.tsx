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
import { CheckEmail } from "./CheckEmail";
import { authCopy } from "./copy";
import { pendingFlow } from "./flows";
import { FormError } from "./FormError";
import { type RegisterValues, registerSchema } from "./schemas";
import { SocialButtons } from "./SocialButtons";
import { useSignedIn } from "./useSignedIn";

const copy = authCopy.register;

export function RegisterForm() {
  const searchParams = useSearchParams();
  const next = searchParams.get("next");
  const signedIn = useSignedIn();
  const [sentTo, setSentTo] = useState<string | null>(null);
  const form = useForm<RegisterValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: { email: "", username: "", password: "" },
  });
  const { errors, isSubmitting } = form.formState;

  async function onSubmit(values: RegisterValues) {
    const { error, response } = await auth.POST("/_allauth/browser/v1/auth/signup", {
      body: values,
    });
    if (response.ok) {
      await signedIn(next);
      return;
    }
    if (response.status === 401 && pendingFlow(error) === "verify_email") {
      setSentTo(values.email);
      return;
    }
    applyErrors(error, form.setError, ["email", "username", "password"], authCopy.errors.generic);
  }

  if (sentTo) {
    return <CheckEmail email={sentTo} />;
  }

  return (
    <div className="flex flex-col gap-8">
      <form onSubmit={form.handleSubmit(onSubmit)} noValidate className="flex flex-col gap-6">
        <FormError message={errors.root?.message} />
        <Input
          label={authCopy.fields.email}
          type="email"
          autoComplete="email"
          error={errors.email?.message}
          {...form.register("email")}
        />
        <Input
          label={authCopy.fields.nickname}
          autoComplete="username"
          hint={authCopy.fields.nicknameHint}
          error={errors.username?.message}
          {...form.register("username")}
        />
        <Input
          label={authCopy.fields.password}
          type="password"
          autoComplete="new-password"
          hint={authCopy.fields.passwordHint}
          error={errors.password?.message}
          {...form.register("password")}
        />
        <p className="text-meta text-muted">
          {copy.terms.before}
          <Link href="/rules" className="underline underline-offset-4">
            {copy.terms.link}
          </Link>
          {copy.terms.after}
        </p>
        <Button type="submit" size="lg" loading={isSubmitting}>
          {copy.submit}
        </Button>
      </form>
      <SocialButtons next={next} />
      <p className="text-sm text-muted">
        {copy.haveAccount}{" "}
        <Link
          href={next ? `/login?next=${encodeURIComponent(next)}` : "/login"}
          className="text-text underline underline-offset-4"
        >
          {copy.login}
        </Link>
      </p>
    </div>
  );
}
