"use client";

import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { Illustration } from "@/components/ui/Illustration";
import { auth } from "@/lib/api/auth-client";

import { authCopy } from "./copy";

const copy = authCopy.checkEmail;

/** Shown after sign-up: the account waits for the email link. */
export function CheckEmail({ email }: { email: string }) {
  const [resent, setResent] = useState(false);

  async function resend() {
    await auth.POST("/_allauth/browser/v1/auth/email/verify/resend");
    setResent(true);
  }

  return (
    <div role="status" className="flex flex-col items-start gap-6">
      <Illustration name="empty" size={96} />
      <h2 className="text-h2">{copy.title}</h2>
      <p>{copy.text(email)}</p>
      <p className="text-sm text-muted">{copy.hint}</p>
      {resent ? (
        <p className="text-sm">{authCopy.login.resent}</p>
      ) : (
        <Button variant="secondary" onClick={resend}>
          {authCopy.login.resend}
        </Button>
      )}
    </div>
  );
}
