import { SESSION_HINT_COOKIE } from "./session-hint";

/** Django's HttpOnly session cookie. */
export const SESSION_COOKIE = "sessionid";

type CookieJar = {
  has(name: string): boolean;
  get(name: string): { value: string } | undefined;
};

/**
 * Signed in, as far as cookies can tell (redirects, which header to render). The session
 * cookie alone is not enough: allauth keeps an anonymous session for a sign-up waiting for
 * the email or a password reset. The hint is set only by a real sign-in (useSignedIn) and
 * dropped on sign-out and on a 401 of /api/v1/me. The API still checks every request.
 */
export function looksSignedIn(jar: CookieJar): boolean {
  return jar.has(SESSION_COOKIE) && jar.get(SESSION_HINT_COOKIE)?.value === "1";
}
