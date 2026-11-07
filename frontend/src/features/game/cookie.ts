/** «Моя гра» of a guest: the `bc_game` cookie, e.g. `1.21.1:fabric` (docs/tech.md, 10.2). */

export const GAME_COOKIE = "bc_game";
export const GAME_COOKIE_MAX_AGE = 60 * 60 * 24 * 365;

export type MyGame = { game_version: string; loader: string };

const VERSION = /^[0-9][0-9a-z.-]{0,31}$/;
const LOADERS = ["fabric", "forge", "neoforge", "quilt", "vanilla"];

/** The shape only; the backend also checks the version is supported. */
export function parseGameCookie(value: string | undefined | null): MyGame | null {
  let decoded = "";
  try {
    decoded = value ? decodeURIComponent(value) : "";
  } catch {
    return null; // a malformed escape such as %E0 must not break the header
  }
  const separator = decoded.indexOf(":");
  if (separator < 0) return null;
  const game_version = decoded.slice(0, separator);
  const loader = decoded.slice(separator + 1);
  if (game_version && !VERSION.test(game_version)) return null;
  if (loader && !LOADERS.includes(loader)) return null;
  return game_version || loader ? { game_version, loader } : null;
}

export function formatGameCookie({ game_version, loader }: MyGame): string {
  return `${game_version}:${loader}`;
}

/** Writes the guest cookie for a year; the server reads it on the next render. */
export function saveGameCookie(game: MyGame): void {
  document.cookie = `${GAME_COOKIE}=${encodeURIComponent(formatGameCookie(game))}; Max-Age=${GAME_COOKIE_MAX_AGE}; Path=/; SameSite=Lax`;
}
