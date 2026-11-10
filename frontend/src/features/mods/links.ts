/** Links to API endpoints that browsers follow directly (no server-only imports here). */

export function downloadUrl(
  slug: string,
  params: { game_version?: string; loader?: string; version?: string },
): string {
  const query = new URLSearchParams(
    Object.entries(params).filter((entry): entry is [string, string] => Boolean(entry[1])),
  );
  return `/api/v1/mods/${encodeURIComponent(slug)}/download${query.size ? `?${query}` : ""}`;
}
