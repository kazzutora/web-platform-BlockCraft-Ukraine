import { cookies } from "next/headers";

import { getServerClient } from "@/lib/api/server-client";
import { looksSignedIn } from "@/lib/session";

import { GAME_COOKIE, type MyGame, parseGameCookie } from "./cookie";
import { getGameVersions } from "./meta";

export type GameContext = MyGame & {
  /** Where it comes from: the player's profile, the guest cookie, or nothing chosen yet. */
  source: "profile" | "cookie" | "none";
};

const NONE: GameContext = { game_version: "", loader: "", source: "none" };

/**
 * «Моя гра» for Server Components: the profile once it has a choice, otherwise the cookie
 * (guests, and players who chose before signing in). Same rules as the backend's
 * `core.game.game_context`. Render inside <Suspense>.
 */
export async function getGameContext(): Promise<GameContext> {
  const jar = await cookies();
  if (looksSignedIn(jar)) {
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
  if (!fromCookie) return NONE;
  // A version that is no longer supported (or never was) would filter everything out
  let { game_version } = fromCookie;
  if (game_version) {
    const supported = await getGameVersions();
    if (supported.length && !supported.includes(game_version)) game_version = "";
  }
  if (!game_version && !fromCookie.loader) return NONE;
  return { game_version, loader: fromCookie.loader, source: "cookie" };
}
