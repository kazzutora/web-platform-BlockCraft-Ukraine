import { getServerClient } from "@/lib/api/server-client";

import type { CatalogQuery } from "./types";

/** Server-side reads of packs (render inside <Suspense>). */
export async function getCatalog(query: CatalogQuery) {
  const client = await getServerClient();
  const { data, response } = await client.GET("/api/v1/packs", { params: { query } });
  if (!data) throw new Error(`GET /api/v1/packs failed: ${response.status}`);
  return data;
}

/** null when the pack does not exist or the viewer may not see it (draft, private, no token). */
export async function getPack(slug: string, shareToken = "") {
  const client = await getServerClient();
  const { data, response } = await client.GET("/api/v1/packs/{slug}", {
    params: { path: { slug }, query: shareToken ? { share_token: shareToken } : {} },
  });
  if (response.status === 404) return null;
  if (!data) throw new Error(`GET /api/v1/packs/${slug} failed: ${response.status}`);
  return data;
}

/** Direct links for installing by hand; empty when the API cannot answer. */
export async function getFiles(slug: string, shareToken = "") {
  const client = await getServerClient();
  const { data } = await client.GET("/api/v1/packs/{slug}/files", {
    params: { path: { slug }, query: shareToken ? { share_token: shareToken } : {} },
  });
  return data ?? [];
}

export function exportUrl(slug: string, shareToken = ""): string {
  const query = shareToken ? `?share_token=${encodeURIComponent(shareToken)}` : "";
  return `/api/v1/packs/${encodeURIComponent(slug)}/export.mrpack${query}`;
}
