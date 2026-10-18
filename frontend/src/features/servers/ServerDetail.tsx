import Image from "next/image";
import Link from "next/link";
import { notFound } from "next/navigation";

import { Container } from "@/components/layout/Container";
import { Badge } from "@/components/ui/Badge";
import { Chip } from "@/components/ui/Chip";
import { Icon } from "@/components/ui/Icon";
import { Tabs } from "@/components/ui/Tabs";
import { AddToCollection } from "@/features/library/AddToCollection";
import { SaveToggle } from "@/features/library/SaveToggle";
import { ReportButton } from "@/features/moderation/ReportButton";
import { Comments } from "@/features/social/Comments";
import { Reviews } from "@/features/social/Reviews";
import { cn } from "@/lib/cn";

import { getServer, getStats } from "./api";
import { serversCopy } from "./copy";
import { CopyAddress } from "./CopyAddress";
import { OnlineChart } from "./OnlineChart";
import { ServerOwnerActions } from "./ServerOwnerActions";
import type { LiveStatus } from "./types";
import { VerifyPanel } from "./VerifyPanel";

const copy = serversCopy.detail;
const live = serversCopy.live;

/** /servers/[slug]: banner, the big online counter, address, chart, reviews. */
export async function ServerDetail({ slug }: { slug: string }) {
  const server = await getServer(slug);
  if (!server) notFound();
  const stats = await getStats(slug);
  const published = server.status === "published";
  const facts = [
    { label: serversCopy.filters.edition, value: serversCopy.editions[server.edition] },
    { label: copy.versions, value: server.versions_label },
    { label: serversCopy.filters.language, value: serversCopy.languages[server.language] },
    {
      label: serversCopy.filters.mode,
      value: server.modes.map((m) => serversCopy.modes[m]).join(", "),
    },
  ].filter((fact) => fact.value);

  return (
    <div className="flex flex-col">
      {!published && (
        <p role="status" className="border-b border-line bg-surface px-4 py-3 text-center text-sm">
          {server.status === "rejected" ? copy.rejected(server.rejection_reason) : copy.pending}
        </p>
      )}
      <Container className="flex flex-col gap-12 py-12 md:py-16">
        {server.banner_url && (
          <div className="aspect-[4/1] w-full overflow-hidden border border-line bg-surface">
            <Image
              src={server.banner_url}
              alt=""
              width={1200}
              height={300}
              unoptimized
              priority
              className="size-full object-cover"
            />
          </div>
        )}

        <header className="grid gap-10 md:grid-cols-[minmax(0,1fr)_auto] md:items-end">
          <div className="flex flex-col gap-6">
            <div className="flex flex-wrap items-center gap-3">
              <Chip tone="servers">{serversCopy.label}</Chip>
              {server.is_verified && <Badge icon="check">{serversCopy.verified}</Badge>}
              {server.has_whitelist && <Badge>{serversCopy.whitelist}</Badge>}
            </div>
            <h1 className="text-h1">{server.name}</h1>
            <div className="flex flex-wrap items-center gap-3">
              <code className="border border-line px-3 py-2 font-mono text-base break-all">
                {server.address}
              </code>
              <CopyAddress
                slug={server.slug}
                address={server.address}
                size="lg"
                variant="primary"
              />
              {published && (
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
              {server.is_mine && <ServerOwnerActions slug={server.slug} />}
              {published && !server.is_mine && <ReportButton kind="server" id={server.slug} />}
            </div>
          </div>
          <OnlineCounter live={server.live} />
        </header>

        {server.is_mine && server.verify_code && (
          <VerifyPanel slug={server.slug} code={server.verify_code} />
        )}

        <Tabs
          label={copy.tabsLabel}
          items={[
            {
              value: "about",
              label: copy.tabs.about,
              content: (
                <div className="grid gap-10 md:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)]">
                  <p className="max-w-prose whitespace-pre-line">
                    {server.description || <span className="text-muted">{copy.noDescription}</span>}
                  </p>
                  <dl className="flex flex-col gap-4">
                    {facts.map((fact) => (
                      <div key={fact.label} className="flex flex-col gap-1">
                        <dt className="text-meta text-muted">{fact.label}</dt>
                        <dd>{fact.value}</dd>
                      </div>
                    ))}
                    <div className="flex flex-col gap-1">
                      <dt className="text-meta text-muted">{copy.owner}</dt>
                      <dd>
                        <Link
                          href={`/u/${server.author.nickname}`}
                          className="underline underline-offset-4"
                        >
                          {server.author.nickname}
                        </Link>
                      </dd>
                    </div>
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
            ...(published
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
                  {
                    value: "comments",
                    label: server.comments_count
                      ? `${copy.tabs.comments} · ${server.comments_count}`
                      : copy.tabs.comments,
                    content: <Comments kind="server" id={server.slug} />,
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
        <span className="font-serif text-display tabular-nums">
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
