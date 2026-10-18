"use client";

import { type ReactNode, createContext, useCallback, useState } from "react";

import { ButtonLink } from "@/components/ui/ButtonLink";
import { Dialog } from "@/components/ui/Dialog";

import { authCopy } from "./copy";
import { rememberPendingAction } from "./pending-action";
import { useMe, useSessionHint } from "./useMe";

const copy = authCopy.prompt;

type RequireAuth = (action?: () => void, options?: { pendingKey?: string }) => boolean;

export const AuthPromptContext = createContext<RequireAuth | null>(null);

/**
 * `requireAuth(action)` runs the action for signed-in users; guests see «Увійди, щоб не
 * загубити» and come back to the same page after signing in. With `pendingKey` the page can
 * replay the action after the return (see usePendingAction).
 */
export function AuthPromptProvider({ children }: { children: ReactNode }) {
  const { me } = useMe();
  const hinted = useSessionHint();
  // The session cookie hint is known at once; /me may still be loading after a quick click
  const signedIn = Boolean(me) || hinted === true;
  const [returnTo, setReturnTo] = useState<string | null>(null);

  const requireAuth = useCallback<RequireAuth>(
    (action, options) => {
      if (signedIn) {
        action?.();
        return true;
      }
      const here = `${window.location.pathname}${window.location.search}`;
      if (options?.pendingKey) rememberPendingAction(options.pendingKey, here);
      setReturnTo(here);
      return false;
    },
    [signedIn],
  );
  const next = encodeURIComponent(returnTo ?? "/");
  const close = () => setReturnTo(null);

  return (
    <AuthPromptContext.Provider value={requireAuth}>
      {children}
      <Dialog
        title={copy.title}
        description={copy.text}
        open={returnTo !== null}
        onOpenChange={(open) => !open && close()}
        footer={
          <>
            <ButtonLink href={`/register?next=${next}`} variant="ghost" onClick={close}>
              {copy.register}
            </ButtonLink>
            <ButtonLink href={`/login?next=${next}`} onClick={close}>
              {copy.login}
            </ButtonLink>
          </>
        }
      />
    </AuthPromptContext.Provider>
  );
}
