import Link from "next/link";

import { buttonClasses } from "@/components/ui/buttonClasses";
import { Icon } from "@/components/ui/Icon";

import { downloadUrl } from "./api";
import { modsCopy } from "./copy";
import type { DownloadTarget } from "./target";
import type { Versions } from "./types";

const copy = modsCopy.detail;

type DownloadActionProps = {
  slug: string;
  target: DownloadTarget;
  versions: Versions | null;
};

/** The one primary action: the right file for the chosen version and loader. */
export function DownloadAction({ slug, target, versions }: DownloadActionProps) {
  if (versions?.recommended) {
    return (
      // A plain <a>: the API answers with a redirect to Modrinth's CDN
      <a
        href={downloadUrl(slug, { game_version: target.gameVersion, loader: target.loader })}
        className={buttonClasses({ size: "lg" })}
      >
        <Icon name="download" />
        {copy.download(target.label)}
      </a>
    );
  }

  const nearest = versions?.nearest_game_versions ?? [];
  return (
    <div role="status" className="flex flex-col gap-3 border border-line p-4 text-sm">
      <p>{target.gameVersion ? copy.noFile(target.label) : copy.noFileAtAll}</p>
      {nearest.length > 0 && (
        <p className="flex flex-wrap items-center gap-2">
          <span className="text-muted">{copy.nearest}</span>
          {nearest.map((version) => (
            <Link
              key={version}
              href={`?${new URLSearchParams({ game_version: version, ...(target.loader ? { loader: target.loader } : {}) })}`}
              className="underline underline-offset-4"
              scroll={false}
            >
              {version}
            </Link>
          ))}
        </p>
      )}
    </div>
  );
}
