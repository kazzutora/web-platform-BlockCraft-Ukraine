import { getServerClient } from "@/lib/api/server-client";

import type { CatalogQuery } from "./types";

/** Server-side reads of packs (render inside <Suspense>). */
export async function getCatalog(query: CatalogQuery) {
  const client = await getServerClient();
  const { data, response } = await client.GET("/api/v1/packs", { params: { query } });
  if (!data) throw new Error(`GET /api/v1/packs failed: ${response.status}`);
  return data;
}

/** null when the pack does not exist or the viewer may not see it (someone else's draft). */
export async function getPack(slug: string) {
  const client = await getServerClient();
  const { data, response } = await client.GET("/api/v1/packs/{slug}", {
    params: { path: { slug } },
  });
  if (response.status === 404) return null;
  if (!data) throw new Error(`GET /api/v1/packs/${slug} failed: ${response.status}`);
  return data;
}
