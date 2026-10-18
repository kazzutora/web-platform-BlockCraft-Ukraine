import { getServerClient } from "@/lib/api/server-client";

import type { CatalogQuery } from "./types";

/** Server-side reads of skins (render inside <Suspense>). */
export async function getCatalog(query: CatalogQuery) {
  const client = await getServerClient();
  const { data, response } = await client.GET("/api/v1/skins", { params: { query } });
  if (!data) throw new Error(`GET /api/v1/skins failed: ${response.status}`);
  return data;
}

/** null when the skin does not exist or the viewer may not see it. */
export async function getSkin(id: number) {
  const client = await getServerClient();
  const { data, response } = await client.GET("/api/v1/skins/{id}", {
    params: { path: { id } },
  });
  if (response.status === 404) return null;
  if (!data) throw new Error(`GET /api/v1/skins/${id} failed: ${response.status}`);
  return data;
}

export async function getSimilar(id: number) {
  const client = await getServerClient();
  const { data } = await client.GET("/api/v1/skins/{id}/similar", { params: { path: { id } } });
  return data ?? [];
}

export function downloadUrl(id: number): string {
  return `/api/v1/skins/${id}/download`;
}
