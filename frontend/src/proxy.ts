import { type NextRequest, NextResponse } from "next/server";

import { SESSION_HINT_COOKIE } from "@/lib/session-hint";

const SESSION_COOKIE = "sessionid";

/** Pages for signed-in users; guests go to /login and come back afterwards. */
const PROTECTED = [
  /^\/me(\/|$)/,
  /^\/welcome$/,
  /^\/create(\/|$)/,
  /^\/skins\/new$/,
  /^\/servers\/new$/,
  /^\/servers\/[^/]+\/edit$/,
];
/** Pages that make no sense once signed in. */
const GUEST_ONLY = [/^\/login$/, /^\/register$/];

/**
 * Checks only that the session cookie exists — enough for redirects; the API still
 * verifies the session on every request.
 */
export function proxy(request: NextRequest) {
  const signedIn = request.cookies.has(SESSION_COOKIE);
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

  // Readable mirror of the HttpOnly session cookie for client code (lib/session-hint.ts)
  const hinted = request.cookies.get(SESSION_HINT_COOKIE)?.value === "1";
  if (signedIn && !hinted) {
    response.cookies.set(SESSION_HINT_COOKIE, "1", {
      path: "/",
      maxAge: 60 * 60 * 24 * 14,
      sameSite: "lax",
    });
  } else if (!signedIn && request.cookies.has(SESSION_HINT_COOKIE)) {
    response.cookies.delete(SESSION_HINT_COOKIE);
  }
  return response;
}

export const config = {
  // Pages only: skip Next.js assets and everything Nginx sends to Django
  matcher: ["/((?!_next/|api/|_allauth/|accounts/|admin/|static/|media/|icon.svg|favicon.ico).*)"],
};
