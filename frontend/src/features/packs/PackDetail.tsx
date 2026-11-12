import Link from "next/link";
import { notFound } from "next/navigation";

import { Container } from "@/components/layout/Container";
import { Chip } from "@/components/ui/Chip";
import { CompatStatus } from "@/components/ui/CompatStatus";
import { SourceBadge } from "@/components/ui/SourceBadge";
import { Tabs } from "@/components/ui/Tabs";
import { TakeButton } from "@/components/ui/TakeButton";
import { ResolutionView } from "@/features/compat/ResolutionView";
import { AddToCollection } from "@/features/library/AddToCollection";
import { SaveToggle } from "@/features/library/SaveToggle";
import { ReportButton } from "@/features/moderation/ReportButton";
import { formatFileSize } from "@/features/mods/format";
import { Reviews } from "@/features/social/Reviews";
import { translationsCopy } from "@/features/translations/copy";
import { TranslationBlock } from "@/features/translations/TranslationBlock";
import { plural } from "@/lib/plural";

import { exportUrl, getFiles, getPack } from "./api";
import { packsCopy } from "./copy";
import { ForkDialog } from "./ForkDialog";
import { PackCover } from "./PackCover";
import { PackInstall } from "./PackInstall";
import { PackModsGrid } from "./PackModsGrid";
import { PackOwnerActions } from "./PackOwnerActions";
import { ShareLink } from "./ShareLink";
import type { PackDetail as Pack } from "./types";

const copy = packsCopy.detail;
const TONES = { ok: "ok", warnings: "warning", errors: "error", unknown: "warning" } as const;

type PackDetailProps = { slug: string; shareToken?: string };

/** /packs/[slug]: the .mrpack first, then what is inside, the check and how to install. */
export async function PackDetail({ slug, shareToken = "" }: PackDetailProps) {
  const [pack, files] = await Promise.all([getPack(slug, shareToken), getFiles(slug, shareToken)]);
  if (!pack) notFound();
  const listed = pack.status === "published" && pack.visibility === "public";
  const target = `${pack.game_version} · ${packsCopy.loaders[pack.loader]}`;
  const token = pack.visibility === "link" ? shareToken || pack.share_token || "" : "";
  const notice =
    pack.status === "draft"
      ? copy.draft
      : pack.status === "rejected"
        ? copy.rejected(pack.rejection_reason)
        : pack.visibility === "private"
          ? copy.private
          : pack.visibility === "link"
            ? copy.byLink
            : "";

  return (
    <div className="flex flex-col">
      {notice && (
        <p role="status" className="border-b border-line bg-surface px-4 py-3 text-center text-sm">
          {notice}
        </p>
      )}
      <Container className="flex flex-col gap-12 py-12 md:py-16">
        <header className="grid gap-10 md:grid-cols-[minmax(0,5fr)_minmax(0,7fr)] md:items-center">
          <div className="relative aspect-square w-full max-w-md border border-line bg-surface">
            <PackCover coverUrl={pack.cover_url} icons={pack.icons} eager />
          </div>
          <div className="flex flex-col gap-6">
            <div className="flex flex-wrap items-center gap-3">
              <Chip tone="packs">{packsCopy.origins[pack.origin]}</Chip>
              <CompatStatus tone={TONES[pack.compat_status]}>
                {packsCopy.compat[pack.compat_status]}
              </CompatStatus>
            </div>
            <h1 className="text-h1">{pack.title}</h1>
            {pack.summary && <p className="max-w-prose text-muted">{pack.summary}</p>}
            {pack.summary_uk_by && (
              <p className="text-meta text-muted">
                {translationsCopy.summaryBy(pack.summary_uk_by.nickname)}
              </p>
            )}
            <p className="text-meta text-muted">
              {[
                target,
                plural(pack.items_count, packsCopy.items),
                formatFileSize(pack.total_size),
              ].join(" · ")}
            </p>
            <div className="flex flex-wrap items-center gap-3">
              {pack.origin === "modrinth" || pack.effective_loader_version ? (
                <TakeButton external href={exportUrl(pack.slug, token)}>
                  {pack.origin === "modrinth" ? copy.downloadModrinth : copy.download}
                </TakeButton>
              ) : (
                <p role="status" className="max-w-prose border border-line p-4 text-sm">
                  {pack.is_mine ? copy.noLoaderVersionMine : copy.noLoaderVersion}
                </p>
              )}
              {pack.status === "published" && (
                <ForkDialog
                  slug={pack.slug}
                  gameVersion={pack.game_version}
                  loader={pack.loader}
                  shareToken={token}
                />
              )}
              {listed && (
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
              {pack.is_mine && pack.origin === "community" && <PackOwnerActions slug={pack.slug} />}
              {listed && !pack.is_mine && <ReportButton kind="pack" id={pack.slug} />}
            </div>
            <Credits pack={pack} />
            {pack.is_mine && pack.share_token && pack.visibility === "link" && (
              <ShareLink slug={pack.slug} token={pack.share_token} />
            )}
          </div>
        </header>

        <Tabs
          label={copy.tabsLabel}
          items={[
            {
              value: "items",
              label: `${copy.tabs.items} · ${pack.items_count}`,
              content: <PackModsGrid items={pack.items} />,
            },
            ...(pack.compat
              ? [
                  {
                    value: "check",
                    label: copy.tabs.check,
                    content: (
                      <ResolutionView
                        resolution={pack.compat}
                        title={copy.tabs.check}
                        live={false}
                        downloads={false}
                      />
                    ),
                  },
                ]
              : []),
            {
              value: "requirements",
              label: copy.tabs.requirements,
              content: <Requirements pack={pack} />,
            },
            {
              value: "install",
              label: copy.tabs.install,
              content: <PackInstall files={files} external={pack.external_files} />,
            },
            {
              value: "about",
              label: copy.tabs.about,
              content: <About pack={pack} />,
            },
            ...(listed
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
      {pack.origin === "community" && (
        <span>
          <span className="text-muted">{copy.by}: </span>
          <Link href={`/u/${pack.author.nickname}`} className="underline underline-offset-4">
            {pack.author.nickname}
          </Link>
        </span>
      )}
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

function About({ pack }: { pack: Pack }) {
  if (pack.origin === "modrinth") {
    return (
      <TranslationBlock
        kind="pack"
        id={pack.slug}
        originalHtml={pack.description_html}
        ukrainianHtml={pack.body_uk_html}
        translator={pack.body_uk_by?.nickname ?? null}
        noDescription={copy.noAbout}
      />
    );
  }
  const html = pack.notes_html;
  if (!html) return <p className="text-muted">{copy.noAbout}</p>;
  return (
    <div className="flex flex-col gap-4">
      {pack.origin === "community" && <h2 className="font-display text-h2">{copy.notes}</h2>}
      {/* Rendered from markdown and sanitized on the server (nh3) */}
      <div className="rich-text" dangerouslySetInnerHTML={{ __html: html }} />
    </div>
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
    { label: facts.count, value: String(pack.items_count) },
    { label: facts.size, value: formatFileSize(pack.total_size) },
  ];
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
