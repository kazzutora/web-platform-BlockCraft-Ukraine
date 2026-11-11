import { type NextRequest, NextResponse } from "next/server";

import { looksSignedIn, SESSION_COOKIE } from "@/lib/session";
import { SESSION_HINT_COOKIE } from "@/lib/session-hint";

/** Pages for signed-in users; guests go to /login and come back afterwards. */
const PROTECTED = [
  /^\/me(\/|$)/,
  /^\/welcome$/,
  /^\/servers\/add$/,
  /^\/skins\/add$/,
  /^\/servers\/[^/]+\/edit$/,
  /^\/packs\/new$/,
  /^\/packs\/[^/]+\/edit$/,
];
/** Pages that make no sense once signed in. */
const GUEST_ONLY = [/^\/login$/, /^\/register$/];

/**
 * Checks only cookies — enough for redirects; the API still verifies the session on every
 * request (see lib/session.ts for why the session cookie alone does not count).
 */
export function proxy(request: NextRequest) {
  const signedIn = looksSignedIn(request.cookies);
  const { pathname, search } = request.nextUrl;

  let response: NextResponse;
  if (!signedIn && PROTECTED.some((pattern) => pattern.test(pathname))) {
    const login = new URL("/login", request.url);
    login.searchParams.set("next", `${pathname}${search}`);
    response = NextResponse.redirect(login);
  } else if (signedIn && GUEST_ONLY.some((pattern) => pattern.test(pathname))) {
    const next = request.nextUrl.searchParams.get("next");
    const target = next?.startsWith("/") && !next.startsWith("//") ? next : "/";
    response = NextResponse.redirect(new URL(target, request.url));
  } else {
    response = NextResponse.next();
  }

  // No session — no hint (signed out elsewhere, the session expired)
  if (!request.cookies.has(SESSION_COOKIE) && request.cookies.has(SESSION_HINT_COOKIE)) {
    response.cookies.delete(SESSION_HINT_COOKIE);
  }
  return response;
}

export const config = {
  // Pages only: skip Next.js assets and everything Nginx sends to Django
  matcher: ["/((?!_next/|api/|_allauth/|accounts/|admin/|static/|media/|icon.svg|favicon.ico).*)"],
};
