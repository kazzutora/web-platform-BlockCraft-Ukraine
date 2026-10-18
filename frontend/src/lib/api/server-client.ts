import { cookies, headers } from "next/headers";
import { connection } from "next/server";
import createClient from "openapi-fetch";

import type { paths } from "./schema";

// Inside Docker the backend is reachable directly; with `pnpm dev` on the host — through Nginx.
const baseUrl = process.env.INTERNAL_API_URL ?? "http://localhost:8080";

/**
 * API client for Server Components: forwards the visitor's cookies (session) and
 * X-Forwarded-For (throttling counts the visitor, not the Next.js server).
 * Responses are per-request, so the caller renders at request time (inside <Suspense>).
 */
export async function getServerClient() {
  await connection();
  const cookieHeader = (await cookies()).toString();
  const forwardedFor = (await headers()).get("x-forwarded-for");
  const forwarded: Record<string, string> = {};
  if (cookieHeader) forwarded.cookie = cookieHeader;
  if (forwardedFor) forwarded["x-forwarded-for"] = forwardedFor;
  return createClient<paths>({ baseUrl, cache: "no-store", headers: forwarded });
}
