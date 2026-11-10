import Image from "next/image";

import { Card } from "@/components/ui/Card";
import { Illustration } from "@/components/ui/Illustration";
import { SourceBadge } from "@/components/ui/SourceBadge";
import { SaveToggle } from "@/features/library/SaveToggle";

import { modsCopy } from "./copy";
import { formatCount, loaderName, mainLoadersOf } from "./format";
import type { ProjectCard } from "./types";

/** «26.3 · Fabric, Quilt · ⬇ 248 млн». */
function meta(project: ProjectCard): string {
  const parts = [project.latest_game_version];
  const loaders = mainLoadersOf(project.loaders);
  if (project.project_type === "mod" && loaders.length) {
    parts.push(loaders.slice(0, 2).map(loaderName).join(", "));
  }
  parts.push(modsCopy.downloads(formatCount(project.downloads)));
  return parts.filter(Boolean).join(" · ");
}

type ModCardProps = {
  project: ProjectCard;
  /** For the first row: it is the largest paint of the catalog. */
  eager?: boolean;
  /** «1.21.1 · Fabric»: named in the «не для …» mark when the project has no files for it. */
  gameLabel?: string;
};

export function ModCard({ project, eager = false, gameLabel = "" }: ModCardProps) {
  return (
    <Card
      href={`/mods/${project.slug}`}
      title={project.title}
      meta={
        <>
          {project.fits_my_game === false && (
            <span className="text-danger">{modsCopy.notForGame(gameLabel)} · </span>
          )}
          {meta(project)} ·{" "}
          <SourceBadge
            {...project.source}
            label={modsCopy.detail.source(project.title, project.source.name)}
          />
        </>
      }
      action={<SaveToggle kind="mod" id={project.slug} saved={project.is_favorited} />}
      cover={
        <div className="flex size-full items-center justify-center p-[18%]">
          {project.icon_url ? (
            <Image
              src={project.icon_url}
              alt=""
              width={192}
              height={192}
              loading={eager ? "eager" : "lazy"}
              className="size-full object-contain"
            />
          ) : (
            <Illustration name="mods" size={96} />
          )}
        </div>
      }
    />
  );
}
