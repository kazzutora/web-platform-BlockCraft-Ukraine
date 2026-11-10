import Image from "next/image";
import Link from "next/link";

import { CompatStatus, type CompatTone } from "@/components/ui/CompatStatus";
import { Icon } from "@/components/ui/Icon";
import { Illustration } from "@/components/ui/Illustration";
import { downloadUrl } from "@/features/mods/api";
import { formatFileSize, loaderName } from "@/features/mods/format";

import type { Resolution, ResolutionItem } from "./api";
import { compatCopy as copy } from "./copy";
import { ResolutionPoller } from "./ResolutionPoller";

export function targetLabel(target: Resolution["target"]): string {
  return [target.game_version, target.loader !== "vanilla" ? loaderName(target.loader) : ""]
    .filter(Boolean)
    .join(" · ");
}

function overall(resolution: Resolution): { tone: CompatTone; text: string } {
  switch (resolution.status) {
    case "ok":
      return { tone: "ok", text: copy.status.ok };
    case "warnings":
      return { tone: "warning", text: copy.status.warnings(resolution.warnings.length) };
    case "incomplete":
      return { tone: "warning", text: copy.status.incomplete };
    default:
      return { tone: "error", text: copy.status.errors };
  }
}

function itemStatus(item: ResolutionItem, target: string): { tone: CompatTone; text: string } {
  const text = copy.item[item.status];
  return {
    tone: item.status === "ok" ? "ok" : "error",
    text: typeof text === "function" ? text(target) : text,
  };
}

function reasonText(item: ResolutionItem, titles: Map<string, string>, loader: string): string {
  const by = item.required_by.map((slug) => titles.get(slug) ?? slug).join(", ");
  if (item.reason === "dependency") return copy.reason.dependency(by);
  if (item.reason === "implicit") return copy.reason.implicit(by, loader);
  return copy.reason.requested;
}

type ResolutionViewProps = { resolution: Resolution };

/** «Що встановити»: conflicts and warnings first, then every file with its reason. */
export function ResolutionView({ resolution }: ResolutionViewProps) {
  const target = targetLabel(resolution.target);
  const titles = new Map(resolution.items.map((item) => [item.project.slug, item.project.title]));
  const status = overall(resolution);
  const params = { game_version: resolution.target.game_version, loader: resolution.target.loader };
  return (
    <section aria-labelledby="install-title" className="flex flex-col gap-6">
      {resolution.status === "incomplete" && (
        <ResolutionPoller
          slug={resolution.items[0]?.project.slug ?? ""}
          target={resolution.target}
        />
      )}
      <header className="flex flex-col gap-2 sm:flex-row sm:items-baseline sm:justify-between">
        <h2 id="install-title" className="font-serif text-h2">
          {copy.title}
        </h2>
        <CompatStatus tone={status.tone}>{status.text}</CompatStatus>
      </header>
      <p className="text-muted">{copy.intro(target)}</p>

      {(resolution.conflicts.length > 0 || resolution.warnings.length > 0) && (
        <ul className="flex flex-col gap-2 border border-line p-4" role="list">
          {resolution.conflicts.map((conflict) => (
            <li key={`${conflict.a}-${conflict.b}`}>
              <CompatStatus tone="error">
                {copy.conflict(
                  titles.get(conflict.a) ?? conflict.a,
                  titles.get(conflict.b) ?? conflict.b,
                  titles.get(conflict.declared_by) ?? conflict.declared_by,
                )}
              </CompatStatus>
            </li>
          ))}
          {resolution.warnings.map((warning, index) => (
            <li key={`${warning.code}-${index}`}>
              <CompatStatus tone="warning">
                {copy.warning[warning.code]({
                  ...warning.params,
                  project: titles.get(warning.params.project ?? "") ?? warning.params.project ?? "",
                  required_by:
                    titles.get(warning.params.required_by ?? "") ??
                    warning.params.required_by ??
                    "",
                })}
              </CompatStatus>
            </li>
          ))}
        </ul>
      )}

      {resolution.missing.length > 0 && <p className="text-meta text-muted">{copy.missing}</p>}
      {resolution.unavailable.length > 0 && (
        <CompatStatus tone="error">{copy.unavailable(resolution.unavailable.length)}</CompatStatus>
      )}

      <ul className="flex flex-col" role="list">
        {resolution.items.map((item) => {
          const state = itemStatus(item, target);
          return (
            <li
              key={item.project.slug}
              className="flex flex-col gap-3 border-b border-line py-4 sm:flex-row sm:items-center"
            >
              <div className="flex min-w-0 flex-1 items-center gap-3">
                <span className="flex size-8 shrink-0 items-center justify-center border border-line bg-surface">
                  {item.project.icon_url ? (
                    <Image src={item.project.icon_url} alt="" width={32} height={32} />
                  ) : (
                    <Illustration name="mods" size={24} />
                  )}
                </span>
                <div className="flex min-w-0 flex-col gap-1">
                  <p className="flex flex-wrap items-baseline gap-x-2">
                    {item.project.hidden ? (
                      <span className="font-medium">{item.project.title}</span>
                    ) : (
                      <Link
                        href={`/mods/${item.project.slug}`}
                        className="font-medium hover:underline"
                      >
                        {item.project.title}
                      </Link>
                    )}
                    {item.version && (
                      <span className="font-mono text-meta text-muted">
                        {item.version.version_number}
                      </span>
                    )}
                  </p>
                  <p className="text-meta text-muted">
                    {reasonText(item, titles, loaderName(resolution.target.loader))}
                    {item.project.hidden && ` · ${copy.hidden}`}
                  </p>
                  {item.nearest_game_versions.length > 0 && (
                    <p className="flex flex-wrap gap-2 text-meta">
                      <span className="text-muted">{copy.nearest}</span>
                      {item.nearest_game_versions.map((version) => (
                        <Link
                          key={version}
                          href={`?${new URLSearchParams({ game_version: version, loader: resolution.target.loader })}`}
                          className="underline underline-offset-4"
                          scroll={false}
                        >
                          {version}
                        </Link>
                      ))}
                    </p>
                  )}
                </div>
              </div>
              <div className="flex items-center justify-between gap-4 sm:justify-end">
                <CompatStatus tone={state.tone}>{state.text}</CompatStatus>
                {item.version && !item.project.hidden && (
                  // A plain <a>: the API redirects to Modrinth's CDN and counts the download
                  <a
                    href={downloadUrl(item.project.slug, { ...params, version: item.version.id })}
                    className="inline-flex shrink-0 items-center gap-2 text-sm underline underline-offset-4"
                    aria-label={`${copy.download} ${item.project.title}, ${formatFileSize(item.version.file_size)}`}
                  >
                    <Icon name="download" size={16} />
                    {formatFileSize(item.version.file_size)}
                  </a>
                )}
              </div>
            </li>
          );
        })}
      </ul>

      {resolution.suggestions.some((suggestion) => suggestion.project) && (
        <p className="flex flex-wrap items-center gap-x-3 gap-y-1 text-meta">
          <span className="text-muted">{copy.suggestions}</span>
          {resolution.suggestions.map((suggestion) =>
            suggestion.project ? (
              <Link
                key={suggestion.project_id}
                href={`/mods/${suggestion.project.slug}`}
                className="underline underline-offset-4"
              >
                {suggestion.project.title}
              </Link>
            ) : null,
          )}
        </p>
      )}
    </section>
  );
}
