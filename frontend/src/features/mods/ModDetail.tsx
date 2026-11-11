import { notFound } from "next/navigation";

import { DetailPage } from "@/components/layout/DetailPage";
import { CardGrid } from "@/components/ui/CardGrid";
import { Chip } from "@/components/ui/Chip";
import { SourceBadge } from "@/components/ui/SourceBadge";
import { getGameContext } from "@/features/game/context";
import { getGameVersions } from "@/features/game/meta";
import { AddToCollection } from "@/features/library/AddToCollection";
import { SaveToggle } from "@/features/library/SaveToggle";
import { ReportButton } from "@/features/moderation/ReportButton";
import { Reviews } from "@/features/social/Reviews";
import { versionDescending } from "@/lib/versions";

import { getProject, getSimilar, getVersions } from "./api";
import { modsCopy } from "./copy";
import { ButtonLink } from "@/components/ui/ButtonLink";
import { TakeButton } from "@/components/ui/TakeButton";
import { getInstall } from "@/features/compat/api";
import { compatCopy } from "@/features/compat/copy";
import { ResolutionView, targetLabel } from "@/features/compat/ResolutionView";

import { downloadUrl } from "./api";
import { formatCount, formatDate, mainLoadersOf } from "./format";
import { ModCard } from "./ModCard";
import { ModGallery } from "./ModGallery";
import { downloadTarget } from "./target";
import { translationsCopy } from "@/features/translations/copy";
import { TranslationBlock } from "@/features/translations/TranslationBlock";
import { VersionPicker } from "./VersionPicker";
import { VersionsList } from "./VersionsList";

const copy = modsCopy.detail;

type ModDetailProps = {
  slug: string;
  searchParams: Record<string, string | string[] | undefined>;
};

/** /mods/[slug]: rendered on the server with the download for the player's setup. */
export async function ModDetail({ slug, searchParams }: ModDetailProps) {
  const [project, profile, supportedVersions] = await Promise.all([
    getProject(slug),
    getGameContext(),
    getGameVersions(),
  ]);
  if (!project) notFound();

  const target = downloadTarget(project, searchParams, profile);
  const [versions, allVersions, similar, resolution] = await Promise.all([
    getVersions(slug, target.gameVersion, target.loader),
    getVersions(slug, "", ""),
    getSimilar(slug),
    getInstall(slug, target),
  ]);
  const own = resolution?.items.find((item) => item.project.slug === slug);
  const label = resolution ? targetLabel(resolution.target) : target.label;
  const nearest = own?.nearest_game_versions[0];
  // The project's versions plus «Моя гра», so the picker shows what the page is about
  const pickerVersions = [...new Set([...project.game_versions, target.gameVersion])]
    .filter((version) => supportedVersions.includes(version))
    .sort(versionDescending);
  const meta = [
    `⬇ ${formatCount(project.downloads)}`,
    project.license && `${copy.license}: ${project.license}`,
    project.updated_at && copy.updated(formatDate(project.updated_at)),
    project.summary_uk_by && translationsCopy.summaryBy(project.summary_uk_by.nickname),
  ]
    .filter(Boolean)
    .join(" · ");

  return (
    <>
      <DetailPage
        media={
          <ModGallery title={project.title} iconUrl={project.icon_url} images={project.gallery} />
        }
        eyebrow={<Chip tone="mods">{modsCopy.types[project.project_type].label}</Chip>}
        title={project.title}
        description={project.summary}
        meta={meta}
        primaryAction={
          <div className="flex w-full flex-col gap-3">
            {pickerVersions.length > 0 && (
              <VersionPicker
                gameVersions={pickerVersions}
                loaders={project.project_type === "mod" ? mainLoadersOf(project.loaders) : []}
                gameVersion={target.gameVersion}
                loader={target.loader}
              />
            )}
            {own?.version ? (
              <TakeButton
                external
                href={downloadUrl(slug, {
                  game_version: resolution?.target.game_version,
                  loader: resolution?.target.loader,
                  version: own.version.id,
                })}
              >
                {compatCopy.downloadFor(label)}
              </TakeButton>
            ) : nearest ? (
              <TakeButton
                fallback
                icon="chevron-right"
                href={`?${new URLSearchParams({ game_version: nearest, loader: resolution?.target.loader ?? "" })}`}
              >
                {compatCopy.nearestButton(nearest)}
              </TakeButton>
            ) : (
              <p role="status" className="border border-line p-4 text-sm">
                {!resolution
                  ? compatCopy.error
                  : own?.status === "mod_needs_loader"
                    ? `${compatCopy.item.mod_needs_loader}. ${compatCopy.changeGame}`
                    : compatCopy.noFiles}
              </p>
            )}
          </div>
        }
        secondaryActions={
          <>
            <SaveToggle
              kind="mod"
              id={project.slug}
              saved={project.is_favorited}
              count={project.favorites_count}
              className="h-12"
            />
            <AddToCollection kind="mod" id={project.slug} />
            {project.project_type !== "datapack" && (
              <ButtonLink
                href={`/packs/new?items=${encodeURIComponent(project.slug)}`}
                variant="ghost"
                size="lg"
              >
                {compatCopy.makePack}
              </ButtonLink>
            )}
            <SourceBadge
              {...project.source}
              label={copy.source(project.title, project.source.name)}
              className="text-sm"
            />
            <ReportButton kind="mod" id={project.slug} />
          </>
        }
        aside={resolution ? <ResolutionView resolution={resolution} /> : null}
        tabsLabel={copy.tabsLabel}
        tabs={[
          {
            value: "about",
            label: copy.tabs.about,
            content: (
              <TranslationBlock
                kind="mod"
                id={project.slug}
                originalHtml={project.body_html}
                ukrainianHtml={project.body_uk_html}
                translator={project.body_uk_by?.nickname ?? null}
                noDescription={copy.noDescription}
              />
            ),
          },
          {
            value: "versions",
            label: copy.tabs.versions,
            content: (
              <VersionsList
                slug={slug}
                matching={versions?.versions ?? []}
                all={allVersions?.versions ?? []}
              />
            ),
          },
          {
            value: "reviews",
            label: project.rating_count
              ? `${copy.tabs.reviews} · ${project.rating_count}`
              : copy.tabs.reviews,
            content: <Reviews kind="mod" id={project.slug} />,
          },
          {
            value: "similar",
            label: copy.tabs.similar,
            content: similar.length ? (
              <CardGrid>
                {similar.map((item) => (
                  <ModCard key={item.slug} project={item} />
                ))}
              </CardGrid>
            ) : (
              <p className="text-muted">{copy.noSimilar}</p>
            ),
          },
        ]}
      />
    </>
  );
}
