import Image from "next/image";
import Link from "next/link";
import { notFound } from "next/navigation";

import { Container } from "@/components/layout/Container";
import { Badge } from "@/components/ui/Badge";
import { Chip } from "@/components/ui/Chip";
import { Icon } from "@/components/ui/Icon";
import { SourceBadge } from "@/components/ui/SourceBadge";
import { Tabs } from "@/components/ui/Tabs";
import { getGameContext } from "@/features/game/context";
import { getMeta } from "@/features/game/meta";
import { AddToCollection } from "@/features/library/AddToCollection";
import { SaveToggle } from "@/features/library/SaveToggle";
import { loaderName } from "@/features/mods/format";
import { ReportButton } from "@/features/moderation/ReportButton";
import { Reviews } from "@/features/social/Reviews";
import { translationsCopy } from "@/features/translations/copy";
import { TranslationBlock } from "@/features/translations/TranslationBlock";
import { cn } from "@/lib/cn";

import { getJoin, getServer, getStats } from "./api";
import { countryName, languageName, serversCopy } from "./copy";
import { CopyAddress } from "./CopyAddress";
import { JoinBlock } from "./JoinBlock";
import { OnlineChart } from "./OnlineChart";
import { categoryName } from "./ServerRow";
import { ServerOwnerActions } from "./ServerOwnerActions";
import type { LiveStatus } from "./types";
import { VerifyPanel } from "./VerifyPanel";

const copy = serversCopy.detail;
const live = serversCopy.live;

/** /servers/[slug]: online, «Щоб зайти», the address; then description, chart, reviews. */
export async function ServerDetail({ slug }: { slug: string }) {
  const server = await getServer(slug);
  if (!server) notFound();
  const [stats, join, game, meta] = await Promise.all([
    getStats(slug),
    getJoin(slug),
    getGameContext(),
    getMeta(),
  ]);
  const listed = server.source !== null || server.is_verified;
  // A pack to take is the main action of a modded server; otherwise it is the address
  const packIsMain = Boolean(join?.kind === "modded" && join.pack);
  const facts = [
    { label: copy.country, value: server.country ? countryName(server.country) : "" },
    { label: copy.languages, value: server.languages.map(languageName).join(", ") },
    {
      label: copy.categories,
      value: server.categories.map((slug) => categoryName(slug, meta.server_categories)).join(", "),
    },
  ].filter((fact) => fact.value);

  return (
    <div className="flex flex-col">
      {!listed && (
        <p role="status" className="border-b border-line bg-surface px-4 py-3 text-center text-sm">
          {copy.waiting}
        </p>
      )}
      <Container className="flex flex-col gap-12 py-12 md:py-16">
        {server.banner_url && (
          <div className="relative aspect-[4/1] w-full overflow-hidden border border-line bg-surface">
            <Image
              src={server.banner_url}
              alt=""
              fill
              sizes="(min-width: 1200px) 1200px, 100vw"
              unoptimized
              priority
              className="object-cover"
            />
          </div>
        )}

        <header className="grid gap-10 md:grid-cols-[minmax(0,1fr)_auto] md:items-end">
          <div className="flex flex-col gap-6">
            <div className="flex flex-wrap items-center gap-3">
              <Chip tone="servers">{serversCopy.kinds[server.content_kind]}</Chip>
              {server.is_verified && <Badge icon="check">{serversCopy.verified}</Badge>}
            </div>
            <div className="flex items-center gap-4">
              {server.icon_url && (
                <div className="relative size-16 shrink-0 overflow-hidden border border-line">
                  <Image src={server.icon_url} alt="" fill sizes="64px" unoptimized />
                </div>
              )}
              <h1 className="text-h1 break-words">{server.name}</h1>
            </div>
            {server.summary && <p className="max-w-prose text-muted">{server.summary}</p>}
            {!server.owner && server.summary_uk_by && (
              <p className="text-meta text-muted">
                {translationsCopy.summaryBy(server.summary_uk_by.nickname)}
              </p>
            )}
            <div className="flex flex-wrap items-center gap-3">
              <code className="border border-line px-3 py-2 font-mono text-base break-all">
                {server.address}
              </code>
              <CopyAddress
                slug={server.slug}
                address={server.address}
                size="lg"
                variant={packIsMain ? "secondary" : "primary"}
              />
              {listed && (
                <>
                  <SaveToggle
                    kind="server"
                    id={server.slug}
                    saved={server.is_favorited}
                    count={server.favorites_count}
                    className="h-12"
                  />
                  <AddToCollection kind="server" id={server.slug} />
                </>
              )}
              {server.is_mine && (
                <ServerOwnerActions slug={server.slug} canDelete={server.source === null} />
              )}
              {listed && !server.is_mine && <ReportButton kind="server" id={server.slug} />}
            </div>
            <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
              {server.source && (
                <SourceBadge
                  {...server.source}
                  label={copy.source(server.name, server.source.name)}
                />
              )}
              {!server.owner && !server.is_claimed_by_me && (
                <Link
                  href={`/servers/add?address=${encodeURIComponent(server.address)}`}
                  className="text-meta text-muted underline underline-offset-4 hover:text-text"
                >
                  {copy.claim}
                </Link>
              )}
            </div>
          </div>
          <OnlineCounter live={server.live} />
        </header>

        {server.is_claimed_by_me && server.verify_code && (
          <VerifyPanel slug={server.slug} code={server.verify_code} />
        )}

        {join && (
          <JoinBlock
            join={join}
            gameLabel={[game.game_version, game.loader && loaderName(game.loader)]
              .filter(Boolean)
              .join(" · ")}
          />
        )}

        <Tabs
          label={copy.tabsLabel}
          items={[
            {
              value: "about",
              label: copy.tabs.about,
              content: (
                <div className="grid gap-10 md:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)]">
                  <div className="flex min-w-0 flex-col gap-8">
                    {server.description_uk_html && (
                      <section className="flex flex-col gap-3">
                        <h3 className="caps font-sans text-muted">{copy.ownerDescription}</h3>
                        {/* Rendered from markdown and sanitized (nh3) on the server */}
                        <div
                          className="rich-text"
                          dangerouslySetInnerHTML={{ __html: server.description_uk_html }}
                        />
                      </section>
                    )}
                    {server.source ? (
                      <TranslationBlock
                        kind="server"
                        id={server.slug}
                        originalHtml={server.description_html}
                        ukrainianHtml={server.body_uk_html}
                        translator={server.body_uk_by?.nickname ?? null}
                        noDescription={copy.noDescription}
                      />
                    ) : (
                      !server.description_uk_html && (
                        <p className="text-muted">{copy.noDescription}</p>
                      )
                    )}
                  </div>
                  <dl className="flex flex-col gap-4">
                    {facts.map((fact) => (
                      <div key={fact.label} className="flex flex-col gap-1">
                        <dt className="text-meta text-muted">{fact.label}</dt>
                        <dd>{fact.value}</dd>
                      </div>
                    ))}
                    {server.owner && (
                      <div className="flex flex-col gap-1">
                        <dt className="text-meta text-muted">{copy.owner}</dt>
                        <dd>
                          <Link
                            href={`/u/${server.owner.nickname}`}
                            className="underline underline-offset-4"
                          >
                            {server.owner.nickname}
                          </Link>
                        </dd>
                      </div>
                    )}
                    {(server.discord_url || server.website_url) && (
                      <div className="flex flex-wrap gap-4 pt-2">
                        {server.discord_url && (
                          <ExternalLink href={server.discord_url}>{copy.discord}</ExternalLink>
                        )}
                        {server.website_url && (
                          <ExternalLink href={server.website_url}>{copy.website}</ExternalLink>
                        )}
                      </div>
                    )}
                  </dl>
                </div>
              ),
            },
            {
              value: "stats",
              label: copy.tabs.stats,
              content: <OnlineChart slug={server.slug} initial={stats} />,
            },
            ...(listed
              ? [
                  {
                    value: "reviews",
                    label: server.rating_count
                      ? `${copy.tabs.reviews} · ${server.rating_count}`
                      : copy.tabs.reviews,
                    content: (
                      <Reviews
                        kind="server"
                        id={server.slug}
                        canReview={!server.is_mine}
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

/** «128» in display type with the green square; «—» when offline or not pinged yet. */
function OnlineCounter({ live: status }: { live: LiveStatus | null }) {
  const online = status?.is_online ?? false;
  return (
    <div className="flex flex-col gap-2 md:items-end md:text-right">
      <p className="flex items-center gap-3">
        <span aria-hidden className={cn("size-4", online ? "bg-accent" : "border border-muted")} />
        <span className="font-display text-display tabular-nums">
          {online ? status?.players_online : "—"}
        </span>
      </p>
      <p className="text-meta text-muted tabular-nums">
        {online && status
          ? `${live.players} · ${live.online(status.players_online, status.players_max)}${status.latency_ms ? ` · ${live.latency(status.latency_ms)}` : ""}`
          : status
            ? live.offline
            : live.unknown}
      </p>
    </div>
  );
}

function ExternalLink({ href, children }: { href: string; children: string }) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer nofollow"
      className="inline-flex items-center gap-2 text-sm underline underline-offset-4"
    >
      <Icon name="external-link" size={16} />
      {children}
    </a>
  );
}
