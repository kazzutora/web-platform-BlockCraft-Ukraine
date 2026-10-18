import { Badge } from "@/components/ui/Badge";
import { Icon } from "@/components/ui/Icon";

import { downloadUrl } from "./api";
import { modsCopy } from "./copy";
import { formatDate, formatFileSize, loaderName } from "./format";
import type { ProjectVersion } from "./types";

const copy = modsCopy.detail;

function VersionRow({ slug, version }: { slug: string; version: ProjectVersion }) {
  const label = version.version_type === "release" ? null : copy[version.version_type];
  return (
    <li className="flex flex-col gap-2 border-b border-line py-4 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex min-w-0 flex-col gap-1">
        <p className="flex flex-wrap items-center gap-2 font-medium">
          <span className="truncate">{version.version_number}</span>
          {label && <Badge>{label}</Badge>}
        </p>
        <p className="text-meta text-muted">
          {[
            version.game_versions.slice(-3).join(", "),
            version.loaders.map(loaderName).join(", "),
            formatFileSize(version.file_size),
            formatDate(version.released_at),
          ]
            .filter(Boolean)
            .join(" · ")}
        </p>
      </div>
      <a
        href={downloadUrl(slug, { version: version.id })}
        className="inline-flex shrink-0 items-center gap-2 text-sm underline underline-offset-4"
      >
        <Icon name="download" size={16} />
        {version.file_name}
      </a>
    </li>
  );
}

type VersionsListProps = {
  slug: string;
  matching: ProjectVersion[];
  all: ProjectVersion[];
};

/** Versions for the chosen version and loader, and every other one folded below. */
export function VersionsList({ slug, matching, all }: VersionsListProps) {
  const matchingIds = new Set(matching.map((version) => version.id));
  const others = all.filter((version) => !matchingIds.has(version.id));
  return (
    <div className="flex flex-col gap-6">
      {matching.length ? (
        <ul>
          {matching.map((version) => (
            <VersionRow key={version.id} slug={slug} version={version} />
          ))}
        </ul>
      ) : (
        <p className="text-muted">{copy.noVersions}</p>
      )}
      {others.length > 0 && (
        <details className="group">
          <summary className="caps flex cursor-pointer list-none items-center gap-2">
            <Icon name="chevron-down" className="transition-transform group-open:rotate-180" />
            {copy.otherVersions} · {others.length}
          </summary>
          <ul className="mt-2">
            {others.map((version) => (
              <VersionRow key={version.id} slug={slug} version={version} />
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}
