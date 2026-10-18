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

/** The player's published skins and public collections for the profile tabs. */
export async function getProfileWorks(nickname: string) {
  const client = await getServerClient();
  const [skins, collections] = await Promise.all([
    client.GET("/api/v1/skins", { params: { query: { author: nickname, sort: "new" } } }),
    client.GET("/api/v1/collections", { params: { query: { owner: nickname } } }),
  ]);
  return { skins: skins.data?.results ?? [], collections: collections.data?.results ?? [] };
}
