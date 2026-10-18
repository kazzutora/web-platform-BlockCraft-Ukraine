import Image from "next/image";
import Link from "next/link";

import { Badge } from "@/components/ui/Badge";

import { modsCopy } from "./copy";
import type { Versions } from "./types";

const copy = modsCopy.detail;

/** Dependencies of the recommended file; catalog entries link to their pages. */
export function DependenciesList({ dependencies }: { dependencies: Versions["dependencies"] }) {
  if (!dependencies.length) return <p className="text-muted">{copy.noDependencies}</p>;
  return (
    <ul className="flex flex-col">
      {dependencies.map((dependency) => (
        <li
          key={dependency.project_id}
          className="flex items-center justify-between gap-4 border-b border-line py-3"
        >
          {dependency.project ? (
            <Link
              href={`/mods/${dependency.project.slug}`}
              className="flex items-center gap-3 font-medium underline-offset-4 hover:underline"
            >
              {dependency.project.icon_url && (
                <Image
                  src={dependency.project.icon_url}
                  alt=""
                  width={32}
                  height={32}
                  className="size-8 border border-line"
                />
              )}
              {dependency.project.title}
            </Link>
          ) : (
            <span className="text-muted">
              {dependency.project_id} · {copy.notInCatalog}
            </span>
          )}
          <Badge tone={dependency.dependency_type === "required" ? "accent" : "neutral"}>
            {copy.dependencyTypes[dependency.dependency_type]}
          </Badge>
        </li>
      ))}
    </ul>
  );
}
