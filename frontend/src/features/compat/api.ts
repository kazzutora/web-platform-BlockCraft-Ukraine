import type { components } from "@/lib/api/schema";
import { getServerClient } from "@/lib/api/server-client";

export type Resolution = components["schemas"]["Resolution"];
export type ResolutionItem = components["schemas"]["ResolutionItem"];

/** «Що встановити» for one project; null when the API could not answer. */
export async function getInstall(
  slug: string,
  target: { gameVersion: string; loader: string },
): Promise<Resolution | null> {
  const client = await getServerClient();
  const query: { game_version?: string; loader?: ResolutionItemLoader } = {};
  if (target.gameVersion) query.game_version = target.gameVersion;
  if (target.loader) query.loader = target.loader as ResolutionItemLoader;
  const { data } = await client.GET("/api/v1/mods/{slug}/install", {
    params: { path: { slug }, query },
  });
  return data ?? null;
}

type ResolutionItemLoader = components["schemas"]["LoaderEnum"];
