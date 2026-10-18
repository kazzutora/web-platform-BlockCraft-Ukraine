import { getServerClient } from "@/lib/api/server-client";

/** Collection for the page; null when it does not exist or the viewer may not see it. */
export async function getCollection(id: number, shareToken: string) {
  const client = await getServerClient();
  const { data, response } = await client.GET("/api/v1/collections/{id}", {
    params: { path: { id: id }, query: shareToken ? { share_token: shareToken } : {} },
  });
  if (response.status === 404) return null;
  if (!data) throw new Error(`GET /api/v1/collections/${id} failed: ${response.status}`);
  return data;
}
