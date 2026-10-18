"use client";

import { type FormEvent, useRef } from "react";

import { buttonClasses } from "@/components/ui/buttonClasses";
import { getCsrfToken } from "@/lib/api/csrf";

import { authCopy } from "./copy";
import { useAuthConfig } from "./useAuthConfig";

/**
 * OAuth buttons for the providers configured on the server. A real form POST:
 * allauth answers with a redirect to Discord / Google and back to /login/callback.
 */
export function SocialButtons({ next }: { next?: string | null }) {
  const { data: config } = useAuthConfig();
  const providers = config?.socialaccount?.providers ?? [];
  if (!providers.length) return null;

  const callback = `/login/callback${next ? `?next=${encodeURIComponent(next)}` : ""}`;

  return (
    <div className="flex flex-col gap-3">
      <p className="caps flex items-center gap-4 text-muted before:h-px before:flex-1 before:bg-line after:h-px after:flex-1 after:bg-line">
        {authCopy.social.divider}
      </p>
      {providers.map((provider) => (
        <ProviderForm key={provider.id} id={provider.id} name={provider.name} callback={callback} />
      ))}
    </div>
  );
}

function ProviderForm({ id, name, callback }: { id: string; name: string; callback: string }) {
  const tokenRef = useRef<HTMLInputElement>(null);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    if (tokenRef.current) tokenRef.current.value = await getCsrfToken();
    form.submit();
  }

  return (
    <form method="post" action="/_allauth/browser/v1/auth/provider/redirect" onSubmit={onSubmit}>
      <input type="hidden" name="provider" value={id} />
      <input type="hidden" name="process" value="login" />
      <input type="hidden" name="callback_url" value={callback} />
      <input ref={tokenRef} type="hidden" name="csrfmiddlewaretoken" value="" />
      <button
        type="submit"
        className={buttonClasses({ variant: "secondary", size: "lg", className: "w-full" })}
      >
        {authCopy.social.continueWith(name)}
      </button>
    </form>
  );
}
