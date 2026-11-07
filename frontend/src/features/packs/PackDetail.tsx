import Link from "next/link";
import { notFound } from "next/navigation";

import { Container } from "@/components/layout/Container";
import { Badge } from "@/components/ui/Badge";
import { Chip } from "@/components/ui/Chip";
import { SourceBadge } from "@/components/ui/SourceBadge";
import { Tabs } from "@/components/ui/Tabs";
import { AddToCollection } from "@/features/library/AddToCollection";
import { SaveToggle } from "@/features/library/SaveToggle";
import { ReportButton } from "@/features/moderation/ReportButton";
import { formatFileSize } from "@/features/mods/format";
import { Reviews } from "@/features/social/Reviews";
import { plural } from "@/lib/plural";

import { getPack } from "./api";
import { packsCopy } from "./copy";
import { PackActions } from "./PackActions";
import { PackCover } from "./PackCover";
import { PackModsGrid } from "./PackModsGrid";
import { PackOwnerActions } from "./PackOwnerActions";
import type { PackDetail as Pack } from "./types";

const copy = packsCopy.detail;

/** /packs/[slug]: cover and the .mrpack first, then mods, requirements, install, reviews. */
export async function PackDetail({ slug }: { slug: string }) {
  const pack = await getPack(slug);
  if (!pack) notFound();
  const published = pack.status === "published";

  return (
    <div className="flex flex-col">
      {!published && (
        <p role="status" className="border-b border-line bg-surface px-4 py-3 text-center text-sm">
          {pack.status === "draft"
            ? copy.draft
            : pack.status === "rejected"
              ? copy.rejected(pack.rejection_reason)
              : copy.pending}
        </p>
      )}
      <Container className="flex flex-col gap-12 py-12 md:py-16">
        <header className="grid gap-10 md:grid-cols-[minmax(0,5fr)_minmax(0,7fr)] md:items-center">
          <div className="relative aspect-square w-full max-w-md border border-line bg-surface">
            <PackCover coverUrl={pack.cover_url} icons={pack.icons} eager />
          </div>
          <div className="flex flex-col gap-6">
            <div className="flex flex-wrap items-center gap-3">
              <Chip tone="packs">{packsCopy.label}</Chip>
              {pack.is_official && <Badge icon="check">{packsCopy.official}</Badge>}
              {pack.style_tags.map((style) => (
                <Badge key={style}>{packsCopy.styles[style]}</Badge>
              ))}
            </div>
            <h1 className="text-h1">{pack.title}</h1>
            {pack.summary && <p className="max-w-prose text-muted">{pack.summary}</p>}
            <p className="text-meta text-muted">
              {[
                pack.game_version,
                packsCopy.loaders[pack.loader],
                plural(pack.mods_count, packsCopy.mods),
                formatFileSize(pack.total_size),
              ].join(" · ")}
            </p>
            <div className="flex flex-wrap items-center gap-3">
              <PackActions slug={pack.slug} official={pack.is_official} canFork={published} />
              {published && (
                <>
                  <SaveToggle
                    kind="pack"
                    id={pack.slug}
                    saved={pack.is_favorited}
                    count={pack.favorites_count}
                    className="h-12"
                  />
                  <AddToCollection kind="pack" id={pack.slug} />
                </>
              )}
              {pack.is_mine && <PackOwnerActions slug={pack.slug} />}
              {published && !pack.is_mine && <ReportButton kind="pack" id={pack.slug} />}
            </div>
            <Credits pack={pack} />
          </div>
        </header>

        <Tabs
          label={copy.tabsLabel}
          items={[
            {
              value: "mods",
              label: `${copy.tabs.mods} · ${pack.mods_count}`,
              content: <PackModsGrid items={pack.items} />,
            },
            {
              value: "requirements",
              label: copy.tabs.requirements,
              content: <Requirements pack={pack} />,
            },
            {
              value: "install",
              label: copy.tabs.install,
              content: pack.install_html ? (
                // install_html is rendered from markdown and sanitized on the server (nh3)
                <div
                  className="rich-text"
                  dangerouslySetInnerHTML={{ __html: pack.install_html }}
                />
              ) : (
                <ol className="flex max-w-prose list-decimal flex-col gap-3 pl-6">
                  {copy.defaultInstall.map((step) => (
                    <li key={step}>{step}</li>
                  ))}
                </ol>
              ),
            },
            {
              value: "changelog",
              label: copy.tabs.changelog,
              content: pack.changelog_html ? (
                <div
                  className="rich-text"
                  dangerouslySetInnerHTML={{ __html: pack.changelog_html }}
                />
              ) : (
                <p className="text-muted">{copy.noChangelog}</p>
              ),
            },
            ...(published
              ? [
                  {
                    value: "reviews",
                    label: pack.rating_count
                      ? `${copy.tabs.reviews} · ${pack.rating_count}`
                      : copy.tabs.reviews,
                    content: (
                      <Reviews
                        kind="pack"
                        id={pack.slug}
                        canReview={!pack.is_mine}
                        hint={copy.reviewsHint}
                      />
                    ),
                  },
                ]
              : []),
          ]}
        />
      </Container>
    </div>
  );
}

function Credits({ pack }: { pack: Pack }) {
  return (
    <p className="flex flex-wrap gap-x-6 gap-y-2 text-sm">
      <span>
        <span className="text-muted">{copy.by}: </span>
        <Link href={`/u/${pack.author.nickname}`} className="underline underline-offset-4">
          {pack.author.nickname}
        </Link>
      </span>
      {pack.forked_from && (
        <span>
          <span className="text-muted">{copy.forkedFrom}: </span>
          <Link href={`/packs/${pack.forked_from.slug}`} className="underline underline-offset-4">
            {pack.forked_from.title}
          </Link>
        </span>
      )}
      {pack.source && (
        <SourceBadge
          {...pack.source}
          label={copy.source(pack.title, pack.source.name)}
          className="text-sm"
        />
      )}
    </p>
  );
}

function Requirements({ pack }: { pack: Pack }) {
  const facts = copy.requirements;
  const loader = `${packsCopy.loaders[pack.loader]} ${
    pack.effective_loader_version || facts.loaderLatest
  }`;
  const rows = [
    { label: facts.game, value: pack.game_version },
    { label: facts.loader, value: loader },
    { label: facts.ram, value: facts.ramValue(pack.ram_min_gb) },
    { label: facts.gpu, value: pack.gpu_note },
    { label: facts.count, value: String(pack.mods_count) },
    { label: facts.size, value: formatFileSize(pack.total_size) },
  ].filter((row) => row.value);
  return (
    <dl className="grid max-w-2xl gap-x-10 gap-y-6 sm:grid-cols-2">
      {rows.map((row) => (
        <div key={row.label} className="flex flex-col gap-1 border-t border-line pt-3">
          <dt className="text-meta text-muted">{row.label}</dt>
          <dd className="tabular-nums">{row.value}</dd>
        </div>
      ))}
    </dl>
  );
}
