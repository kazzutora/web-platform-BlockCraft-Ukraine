import { cookies } from "next/headers";
import { connection } from "next/server";
import createClient from "openapi-fetch";

import type { paths } from "./schema";

// Inside Docker the backend is reachable directly; with `pnpm dev` on the host — through Nginx.
const baseUrl = process.env.INTERNAL_API_URL ?? "http://localhost:8080";

/**
 * API client for Server Components: forwards the visitor's cookies to Django.
 * Responses are per-request, so the caller renders at request time (inside <Suspense>).
 */
export async function getServerClient() {
  await connection();
  const cookieHeader = (await cookies()).toString();
  return createClient<paths>({
    baseUrl,
    cache: "no-store",
    headers: cookieHeader ? { cookie: cookieHeader } : undefined,
  });
}
