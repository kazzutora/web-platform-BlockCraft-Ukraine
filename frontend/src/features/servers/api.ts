import { getServerClient } from "@/lib/api/server-client";

import type { CatalogQuery, StatsRange } from "./types";

/** Server-side reads of servers (render inside <Suspense>). */
export async function getCatalog(query: CatalogQuery) {
  const client = await getServerClient();
  const { data, response } = await client.GET("/api/v1/servers", { params: { query } });
  if (!data) throw new Error(`GET /api/v1/servers failed: ${response.status}`);
  return data;
}

/** null when the server does not exist or the viewer may not see it. */
export async function getServer(slug: string) {
  const client = await getServerClient();
  const { data, response } = await client.GET("/api/v1/servers/{slug}", {
    params: { path: { slug } },
  });
  if (response.status === 404) return null;
  if (!data) throw new Error(`GET /api/v1/servers/${slug} failed: ${response.status}`);
  return data;
}

export async function getStats(slug: string, range: StatsRange = "24h") {
  const client = await getServerClient();
  const { data } = await client.GET("/api/v1/servers/{slug}/stats", {
    params: { path: { slug }, query: { range } },
  });
  return data ?? null;
}
