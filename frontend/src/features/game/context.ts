import { cookies } from "next/headers";

import { getServerClient } from "@/lib/api/server-client";

import { GAME_COOKIE, type MyGame, parseGameCookie } from "./cookie";

export type GameContext = MyGame & {
  /** Where it comes from: the player's profile, the guest cookie, or nothing chosen yet. */
  source: "profile" | "cookie" | "none";
};

const NONE: GameContext = { game_version: "", loader: "", source: "none" };

/**
 * «Моя гра» for Server Components: the profile once it has a choice, otherwise the cookie
 * (guests, and players who chose before signing in). Render inside <Suspense>.
 */
export async function getGameContext(): Promise<GameContext> {
  const jar = await cookies();
  if (jar.has("sessionid")) {
    const client = await getServerClient();
    const { data } = await client.GET("/api/v1/me/game");
    if (data && (data.game_version || data.loader)) {
      return {
        game_version: data.game_version ?? "",
        loader: data.loader ?? "",
        source: "profile",
      };
    }
  }
  const fromCookie = parseGameCookie(jar.get(GAME_COOKIE)?.value);
  return fromCookie ? { ...fromCookie, source: "cookie" } : NONE;
}
