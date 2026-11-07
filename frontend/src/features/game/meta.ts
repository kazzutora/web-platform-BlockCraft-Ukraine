import { getServerClient } from "@/lib/api/server-client";
import type { components } from "@/lib/api/schema";

export type Meta = components["schemas"]["Meta"];

/** Supported game versions, loaders and categories (GET /meta); render inside <Suspense>. */
export async function getMeta(): Promise<Meta> {
  const client = await getServerClient();
  const { data, response } = await client.GET("/api/v1/meta");
  if (!data) throw new Error(`GET /api/v1/meta failed: ${response.status}`);
  return data;
}

/**
 * Supported versions, newest first: synced from Modrinth, never a static list. Empty when
 * /meta fails, so filters lose the version list instead of the whole page failing.
 */
export async function getGameVersions(): Promise<string[]> {
  try {
    return (await getMeta()).game_versions.map((item) => item.version);
  } catch (error) {
    console.error(error);
    return [];
  }
}
