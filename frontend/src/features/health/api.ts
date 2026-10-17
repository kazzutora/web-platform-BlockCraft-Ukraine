import type { components } from "@/lib/api/schema";
import { getServerClient } from "@/lib/api/server-client";

export type Health = components["schemas"]["Health"];

/** Returns the health report (also for 503), or null when the API is unreachable. */
export async function getHealth(): Promise<Health | null> {
  try {
    const client = await getServerClient();
    const { data, error } = await client.GET("/api/v1/health");
    return data ?? error ?? null;
  } catch {
    return null;
  }
}
