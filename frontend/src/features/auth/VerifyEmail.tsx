"use client";

import { useQuery } from "@tanstack/react-query";
import { useEffect } from "react";

import { ButtonLink } from "@/components/ui/ButtonLink";
import { Skeleton } from "@/components/ui/Skeleton";
import { auth } from "@/lib/api/auth-client";

import { authCopy } from "./copy";
import { useSignedIn } from "./useSignedIn";

const copy = authCopy.verify;

type Result = "signed-in" | "verified" | "invalid";

/** Confirms the email from the link; signs in when the link opens in the sign-up browser. */
export function VerifyEmail({ emailKey }: { emailKey: string }) {
  const signedIn = useSignedIn();
  const { data: result } = useQuery({
    queryKey: ["auth", "verify-email", emailKey],
    queryFn: async (): Promise<Result> => {
      const { response } = await auth.POST("/_allauth/browser/v1/auth/email/verify", {
        body: { key: emailKey },
      });
      if (response.ok) return "signed-in";
      // 401: verified, but sign-in continues in another browser
      return response.status === 401 ? "verified" : "invalid";
    },
    retry: false,
    staleTime: Infinity,
  });

  useEffect(() => {
    if (result === "signed-in") void signedIn("/");
  }, [result, signedIn]);

  if (!result || result === "signed-in") {
    return (
      <div role="status" className="flex flex-col gap-4">
        <p>{copy.checking}</p>
        <Skeleton className="h-12 w-48" />
      </div>
    );
  }

  return (
    <div role="status" className="flex flex-col items-start gap-6">
      <p>{result === "verified" ? copy.done : copy.invalid}</p>
      <ButtonLink href="/login" size="lg">
        {copy.login}
      </ButtonLink>
    </div>
  );
}
