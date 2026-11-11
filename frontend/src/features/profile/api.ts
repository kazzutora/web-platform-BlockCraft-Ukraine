import type { components } from "@/lib/api/schema";
import { getServerClient } from "@/lib/api/server-client";

export type PublicProfile = components["schemas"]["PublicProfile"];

/** Public profile or null when there is no such active user. */
export async function getPublicProfile(nickname: string): Promise<PublicProfile | null> {
  const client = await getServerClient();
  const { data, response } = await client.GET("/api/v1/users/{nickname}", {
    params: { path: { nickname } },
  });
  if (response.status === 404) return null;
  if (!data) throw new Error(`GET /api/v1/users/${nickname} failed: ${response.status}`);
  return data;
}

/** What the player shared (anyone may see) and their public collections. */
export async function getProfileWorks(nickname: string) {
  const client = await getServerClient();
  const [shared, collections] = await Promise.all([
    client.GET("/api/v1/users/{nickname}/shared", { params: { path: { nickname } } }),
    client.GET("/api/v1/collections", { params: { query: { owner: nickname } } }),
  ]);
  return { shared: shared.data ?? null, collections: collections.data?.results ?? [] };
}
