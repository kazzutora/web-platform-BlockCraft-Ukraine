import { getServerClient } from "@/lib/api/server-client";

/** Home blocks for the current viewer (cached ids on the server, personal state per request). */
export async function getHome() {
  const client = await getServerClient();
  const { data, response } = await client.GET("/api/v1/home");
  if (!data) throw new Error(`GET /api/v1/home failed: ${response.status}`);
  return data;
}
