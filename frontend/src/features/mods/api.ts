import { cookies } from "next/headers";

import { getServerClient } from "@/lib/api/server-client";

import type { CatalogQuery } from "./types";

/** Server-side reads of the mods catalog (render inside <Suspense>). */
export async function getCatalog(query: CatalogQuery) {
  const client = await getServerClient();
  const { data, response } = await client.GET("/api/v1/mods", { params: { query } });
  if (!data) throw new Error(`GET /api/v1/mods failed: ${response.status}`);
  return data;
}

export async function getCategories(type: CatalogQuery["type"]) {
  const client = await getServerClient();
  const { data } = await client.GET("/api/v1/categories", { params: { query: { type } } });
  return data ?? [];
}

export async function getProject(slug: string) {
  const client = await getServerClient();
  const { data, response } = await client.GET("/api/v1/mods/{slug}", {
    params: { path: { slug } },
  });
  if (response.status === 404) return null;
  if (!data) throw new Error(`GET /api/v1/mods/${slug} failed: ${response.status}`);
  return data;
}

export async function getVersions(slug: string, gameVersion: string, loader: string) {
  const client = await getServerClient();
  const { data } = await client.GET("/api/v1/mods/{slug}/versions", {
    params: { path: { slug }, query: { game_version: gameVersion, loader } },
  });
  return data ?? null;
}

export async function getSimilar(slug: string) {
  const client = await getServerClient();
  const { data } = await client.GET("/api/v1/mods/{slug}/similar", {
    params: { path: { slug } },
  });
  return data ?? [];
}

/** The signed-in player's game profile: defaults for filters and downloads. */
export async function getGameProfile() {
  // Guests have no profile: skip the request instead of collecting a 401
  if (!(await cookies()).has("sessionid")) return null;
  const client = await getServerClient();
  const { data } = await client.GET("/api/v1/me");
  return data?.game_profile ?? null;
}

export function downloadUrl(
  slug: string,
  params: { game_version?: string; loader?: string; version?: string },
): string {
  const query = new URLSearchParams(
    Object.entries(params).filter((entry): entry is [string, string] => Boolean(entry[1])),
  );
  return `/api/v1/mods/${encodeURIComponent(slug)}/download${query.size ? `?${query}` : ""}`;
}
