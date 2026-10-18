import Image from "next/image";

import { Card } from "@/components/ui/Card";
import { Illustration } from "@/components/ui/Illustration";

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

/** `eager` for the first row: it is the largest paint of the catalog. */
export function ModCard({ project, eager = false }: { project: ProjectCard; eager?: boolean }) {
  return (
    <Card
      href={`/mods/${project.slug}`}
      title={project.title}
      meta={meta(project)}
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
