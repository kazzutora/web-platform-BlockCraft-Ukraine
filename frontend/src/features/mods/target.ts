import { loaderName, mainLoadersOf } from "./format";
import type { ProjectDetail } from "./types";

type Profile = { game_version?: string; loader?: string } | null;
type SearchParams = Record<string, string | string[] | undefined>;

export type DownloadTarget = { gameVersion: string; loader: string; label: string };

const pick = (value: string | string[] | undefined) =>
  (Array.isArray(value) ? value[0] : value) ?? "";

/**
 * What to download: the URL wins, then the player's profile, then the newest release the
 * project supports. The loader matters only for mods.
 */
export function downloadTarget(
  project: ProjectDetail,
  params: SearchParams,
  profile: Profile,
): DownloadTarget {
  const supports = (version: string) => project.game_versions.includes(version);
  const requested = pick(params.game_version);
  const fromProfile =
    profile?.game_version && supports(profile.game_version) ? profile.game_version : "";
  const gameVersion = requested || fromProfile || project.latest_game_version;

  let loader = "";
  if (project.project_type === "mod") {
    const loaders = mainLoadersOf(project.loaders);
    const profileLoader = profile?.loader && loaders.includes(profile.loader) ? profile.loader : "";
    loader = pick(params.loader) || profileLoader || loaders[0] || project.loaders[0] || "";
  }
  const label = [gameVersion, loader && loaderName(loader)].filter(Boolean).join(" · ");
  return { gameVersion, loader, label };
}
