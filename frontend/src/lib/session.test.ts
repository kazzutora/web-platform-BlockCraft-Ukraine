import { NextRequest } from "next/server";
import { describe, expect, it } from "vitest";

import { proxy } from "@/proxy";

import { looksSignedIn } from "./session";

function jar(cookies: Record<string, string>) {
  return {
    has: (name: string) => name in cookies,
    get: (name: string) => (name in cookies ? { value: cookies[name] } : undefined),
  };
}

function request(path: string, cookie: string) {
  return new NextRequest(new URL(path, "http://localhost:8080"), { headers: { cookie } });
}

describe("looksSignedIn", () => {
  it("needs the session and the sign-in hint", () => {
    expect(looksSignedIn(jar({ sessionid: "x", bc_signed_in: "1" }))).toBe(true);
    // allauth's anonymous session of a pending sign-up or a password reset
    expect(looksSignedIn(jar({ sessionid: "x" }))).toBe(false);
    expect(looksSignedIn(jar({ bc_signed_in: "1" }))).toBe(false);
  });
});

describe("proxy", () => {
  it("lets a pending-flow session open /login", () => {
    const response = proxy(request("/login", "sessionid=x"));

    expect(response.headers.get("location")).toBeNull();
    // and does not pretend the visitor is signed in
    expect(response.cookies.get("bc_signed_in")).toBeUndefined();
  });

  it("sends a signed-in player away from /login and a guest to it", () => {
    const signedIn = proxy(request("/login?next=/me", "sessionid=x; bc_signed_in=1"));
    expect(new URL(signedIn.headers.get("location") ?? "").pathname).toBe("/me");

    const guest = proxy(request("/me", "sessionid=x"));
    expect(new URL(guest.headers.get("location") ?? "").pathname).toBe("/login");
  });

  it("drops the hint without a session", () => {
    const response = proxy(request("/", "bc_signed_in=1"));

    expect(response.cookies.get("bc_signed_in")?.value).toBe("");
  });
});
