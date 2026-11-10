import { loaderName, mainLoadersOf } from "./format";
import type { ProjectDetail } from "./types";

type Profile = { game_version?: string | null; loader?: string } | null;
type SearchParams = Record<string, string | string[] | undefined>;

export type DownloadTarget = { gameVersion: string; loader: string; label: string };

const pick = (value: string | string[] | undefined) =>
  (Array.isArray(value) ? value[0] : value) ?? "";

/**
 * What to download: the URL wins, then «Моя гра», then the newest release the
 * project supports. The loader matters only for mods.
 */
export function downloadTarget(
  project: ProjectDetail,
  params: SearchParams,
  profile: Profile,
): DownloadTarget {
  const requested = pick(params.game_version);
  // «Моя гра» stays the target even when the project has no file for it: the page then
  // says so and offers the nearest version instead of quietly showing another one
  const fromProfile = profile?.game_version ?? "";
  const gameVersion = requested || fromProfile || project.latest_game_version;

  let loader = "";
  if (project.project_type === "mod") {
    const loaders = mainLoadersOf(project.loaders);
    const profileLoader = profile?.loader ?? "";
    loader = pick(params.loader) || profileLoader || loaders[0] || project.loaders[0] || "";
  }
  const label = [gameVersion, loader && loaderName(loader)].filter(Boolean).join(" · ");
  return { gameVersion, loader, label };
}
