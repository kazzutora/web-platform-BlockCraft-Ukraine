import { readCookie } from "./api/csrf";

/**
 * Readable mirror of the HttpOnly session cookie, kept in sync by proxy.ts on every page
 * request and by the sign-in / sign-out code. Lets client code skip /api/v1/me for guests
 * instead of collecting 401s.
 */
export const SESSION_HINT_COOKIE = "bc_signed_in";

const listeners = new Set<() => void>();

export function hasSessionHint(): boolean {
  return readCookie(SESSION_HINT_COOKIE) === "1";
}

export function setSessionHint(signedIn: boolean): void {
  document.cookie = signedIn
    ? `${SESSION_HINT_COOKIE}=1; path=/; max-age=${60 * 60 * 24 * 14}; samesite=lax`
    : `${SESSION_HINT_COOKIE}=; path=/; max-age=0; samesite=lax`;
  listeners.forEach((listener) => listener());
}

/** For useSyncExternalStore. */
export function subscribeSessionHint(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}
