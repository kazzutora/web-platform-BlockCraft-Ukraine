"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "next/navigation";
import { useEffect } from "react";
import { useForm } from "react-hook-form";

import { Button } from "@/components/ui/Button";
import { ButtonLink } from "@/components/ui/ButtonLink";
import { Input } from "@/components/ui/Input";
import { Skeleton } from "@/components/ui/Skeleton";
import { auth } from "@/lib/api/auth-client";

import { applyErrors } from "./applyErrors";
import { authCopy } from "./copy";
import { pendingFlow } from "./flows";
import { FormError } from "./FormError";
import { type ProviderSignupValues, providerSignupSchema } from "./schemas";
import { useSignedIn } from "./useSignedIn";

const copy = authCopy.providerSignup;

type State = "signed-in" | "signup" | "failed";

/** Back from Discord / Google: either signed in, or a nickname is still needed. */
export function ProviderCallback() {
  const searchParams = useSearchParams();
  const next = searchParams.get("next");
  const failed = searchParams.has("error");
  const signedIn = useSignedIn();

  const { data: state } = useQuery({
    queryKey: ["auth", "provider-callback"],
    enabled: !failed,
    queryFn: async (): Promise<State> => {
      const { error, response } = await auth.GET("/_allauth/browser/v1/auth/session");
      if (response.ok) return "signed-in";
      return pendingFlow(error) === "provider_signup" ? "signup" : "failed";
    },
    retry: false,
    staleTime: Infinity,
  });

  useEffect(() => {
    if (state === "signed-in") void signedIn(next);
  }, [state, signedIn, next]);

  if (failed || state === "failed") {
    return (
      <div role="status" className="flex flex-col items-start gap-6">
        <FormError message={authCopy.login.socialError} />
        <ButtonLink href="/login" size="lg">
          {authCopy.login.submit}
        </ButtonLink>
      </div>
    );
  }
  if (state === "signup") return <ProviderSignup next={next} />;

  return (
    <div role="status" className="flex flex-col gap-4">
      <p>{copy.checking}</p>
      <Skeleton className="h-12 w-48" />
    </div>
  );
}

/** The provider gave too little data: ask for the nickname (and email if missing). */
function ProviderSignup({ next }: { next: string | null }) {
  const { data: email } = useQuery({
    queryKey: ["auth", "provider-signup"],
    queryFn: async () => {
      const { data } = await auth.GET("/_allauth/browser/v1/auth/provider/signup");
      return data?.data.email[0]?.email ?? "";
    },
    retry: false,
    staleTime: Infinity,
  });
  if (email === undefined) return <Skeleton className="h-48 w-full" />;
  return <ProviderSignupForm next={next} email={email} />;
}

function ProviderSignupForm({ next, email }: { next: string | null; email: string }) {
  const signedIn = useSignedIn();
  const form = useForm<ProviderSignupValues>({
    resolver: zodResolver(providerSignupSchema),
    defaultValues: { email, username: "" },
  });
  const { errors, isSubmitting } = form.formState;

  async function onSubmit(values: ProviderSignupValues) {
    const { error, response } = await auth.POST("/_allauth/browser/v1/auth/provider/signup", {
      body: values,
    });
    if (response.ok) {
      await signedIn(next);
      return;
    }
    applyErrors(error, form.setError, ["email", "username"], authCopy.errors.generic);
  }

  return (
    <form onSubmit={form.handleSubmit(onSubmit)} noValidate className="flex flex-col gap-6">
      <div className="flex flex-col gap-2">
        <h2 className="text-h2">{copy.title}</h2>
        <p className="text-muted">{copy.description}</p>
      </div>
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
        hint={authCopy.fields.nicknameHint}
        error={errors.username?.message}
        {...form.register("username")}
      />
      <Button type="submit" size="lg" loading={isSubmitting}>
        {copy.submit}
      </Button>
    </form>
  );
}
