import { notFound } from "next/navigation";

import { DetailPage } from "@/components/layout/DetailPage";
import { CardGrid } from "@/components/ui/CardGrid";
import { Chip } from "@/components/ui/Chip";
import { Icon } from "@/components/ui/Icon";
import { gameVersions as supportedVersions } from "@/features/game/labels";
import { AddToCollection } from "@/features/library/AddToCollection";
import { SaveToggle } from "@/features/library/SaveToggle";
import { Comments } from "@/features/social/Comments";
import { Reviews } from "@/features/social/Reviews";
import { versionDescending } from "@/lib/versions";

import { getGameProfile, getProject, getSimilar, getVersions } from "./api";
import { modsCopy } from "./copy";
import { DependenciesList } from "./DependenciesList";
import { DownloadAction } from "./DownloadAction";
import { formatCount, formatDate, mainLoadersOf } from "./format";
import { ModCard } from "./ModCard";
import { ModGallery } from "./ModGallery";
import { downloadTarget } from "./target";
import { TranslationBanner } from "./TranslationBanner";
import { VersionPicker } from "./VersionPicker";
import { VersionsList } from "./VersionsList";

const copy = modsCopy.detail;

type ModDetailProps = {
  slug: string;
  searchParams: Record<string, string | string[] | undefined>;
};

/** /mods/[slug]: rendered on the server with the download for the player's setup. */
export async function ModDetail({ slug, searchParams }: ModDetailProps) {
  const [project, profile] = await Promise.all([getProject(slug), getGameProfile()]);
  if (!project) notFound();

  const target = downloadTarget(project, searchParams, profile);
  const [versions, allVersions, similar] = await Promise.all([
    getVersions(slug, target.gameVersion, target.loader),
    getVersions(slug, "", ""),
    getSimilar(slug),
  ]);
  const pickerVersions = project.game_versions
    .filter((version) => supportedVersions.includes(version as never))
    .sort(versionDescending);
  const meta = [
    `⬇ ${formatCount(project.downloads)}`,
    project.license && `${copy.license}: ${project.license}`,
    project.updated_at && copy.updated(formatDate(project.updated_at)),
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
            <DownloadAction slug={slug} target={target} versions={versions} />
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
            <a
              href={project.modrinth_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 text-sm underline underline-offset-4"
            >
              <Icon name="external-link" size={16} />
              {copy.modrinth}
            </a>
          </>
        }
        tabsLabel={copy.tabsLabel}
        tabs={[
          {
            value: "about",
            label: copy.tabs.about,
            content: (
              <div className="flex flex-col gap-6">
                {project.needs_translation && <TranslationBanner projectId={project.id} />}
                {project.body_html ? (
                  // body_html is sanitized on the server (nh3) when synced from Modrinth
                  <div
                    className="rich-text"
                    dangerouslySetInnerHTML={{ __html: project.body_html }}
                  />
                ) : (
                  <p className="text-muted">{copy.noDescription}</p>
                )}
              </div>
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
            value: "dependencies",
            label: copy.tabs.dependencies,
            content: <DependenciesList dependencies={versions?.dependencies ?? []} />,
          },
          {
            value: "reviews",
            label: project.rating_count
              ? `${copy.tabs.reviews} · ${project.rating_count}`
              : copy.tabs.reviews,
            content: <Reviews kind="mod" id={project.slug} />,
          },
          {
            value: "comments",
            label: project.comments_count
              ? `${copy.tabs.comments} · ${project.comments_count}`
              : copy.tabs.comments,
            content: <Comments kind="mod" id={project.slug} />,
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
