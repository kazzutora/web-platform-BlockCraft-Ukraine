import Image from "next/image";
import Link from "next/link";
import type { ReactNode } from "react";

import { Badge } from "@/components/ui/Badge";
import { Illustration } from "@/components/ui/Illustration";
import { SourceBadge } from "@/components/ui/SourceBadge";
import { SaveToggle } from "@/features/library/SaveToggle";

import { countryName, languageName, serversCopy } from "./copy";
import { CopyAddress } from "./CopyAddress";
import { OnlineStatus } from "./OnlineStatus";
import type { ServerCard, ServerCategory } from "./types";

/** Ukrainian name of a Modrinth server category; unknown ones stay as they are. */
export function categoryName(slug: string, categories: ServerCategory[]): string {
  return categories.find((category) => category.slug === slug)?.name ?? slug;
}

/** «SMP, Економіка · українська · Україна · Без модів 1.21.1 · ★ 4.6». */
function meta(server: ServerCard, categories: ServerCategory[]): string {
  const needs =
    server.content_kind === "modded"
      ? serversCopy.card.pack
      : [serversCopy.kinds.vanilla, server.recommended_version || server.supported_versions[0]]
          .filter(Boolean)
          .join(" ");
  return [
    server.categories
      .slice(0, 3)
      .map((slug) => categoryName(slug, categories))
      .join(", "),
    server.languages.slice(0, 3).map(languageName).join(", "),
    server.country ? countryName(server.country) : "",
    needs,
    server.rating_count
      ? `★ ${server.rating_avg.toLocaleString("uk-UA", { maximumFractionDigits: 1 })}`
      : "",
  ]
    .filter(Boolean)
    .join(" · ");
}

type ServerRowProps = {
  server: ServerCard;
  categories?: ServerCategory[];
  badge?: ReactNode;
};

/** Catalog row: icon, name, what is needed to join, live online, address with «Скопіювати IP». */
export function ServerRow({ server, categories = [], badge }: ServerRowProps) {
  return (
    <li className="group relative grid gap-4 border-b border-line py-6 md:grid-cols-[minmax(0,1fr)_auto_auto] md:items-center md:gap-8">
      <div className="flex min-w-0 gap-4">
        <div className="relative size-14 shrink-0 overflow-hidden border border-line bg-surface">
          {server.icon_url ? (
            <Image
              src={server.icon_url}
              alt=""
              fill
              sizes="56px"
              unoptimized
              className="object-cover"
            />
          ) : (
            <Illustration name="servers" size={56} />
          )}
        </div>
        <div className="flex min-w-0 flex-col gap-2">
          <div className="flex flex-wrap items-center gap-3">
            <h3 className="font-sans text-card font-medium">
              {/* The whole row opens the server; the buttons stay above the link */}
              <Link href={`/servers/${server.slug}`} className="after:absolute after:inset-0">
                {server.name}
              </Link>
            </h3>
            {server.is_verified && <Badge icon="check">{serversCopy.verified}</Badge>}
            {badge}
          </div>
          {server.summary && <p className="line-clamp-2 text-sm text-muted">{server.summary}</p>}
          <p className="text-meta text-muted">
            {meta(server, categories)}
            {server.source && (
              <>
                {" · "}
                <SourceBadge
                  {...server.source}
                  label={serversCopy.card.source(server.name, server.source.name)}
                />
              </>
            )}
          </p>
        </div>
      </div>
      <OnlineStatus live={server.live} />
      <div className="relative z-10 flex flex-wrap items-center gap-3">
        <code className="font-mono text-sm break-all">{server.address}</code>
        <CopyAddress slug={server.slug} address={server.address} />
        <SaveToggle kind="server" id={server.slug} saved={server.is_favorited} />
      </div>
    </li>
  );
}
