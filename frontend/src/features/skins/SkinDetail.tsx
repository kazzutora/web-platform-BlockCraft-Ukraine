import Link from "next/link";
import { notFound } from "next/navigation";

import { DetailPage } from "@/components/layout/DetailPage";
import { buttonClasses } from "@/components/ui/buttonClasses";
import { CardGrid } from "@/components/ui/CardGrid";
import { Chip } from "@/components/ui/Chip";
import { Icon } from "@/components/ui/Icon";
import { AddToCollection } from "@/features/library/AddToCollection";
import { LikeButton } from "@/features/library/LikeButton";
import { SaveToggle } from "@/features/library/SaveToggle";
import { formatCount } from "@/features/mods/format";
import { Comments } from "@/features/social/Comments";

import { downloadUrl, getSimilar, getSkin } from "./api";
import { skinsCopy } from "./copy";
import { HowToInstall } from "./HowToInstall";
import { SkinCard } from "./SkinCard";
import { SkinOwnerActions } from "./SkinOwnerActions";
import { SkinViewer } from "./SkinViewer";

const copy = skinsCopy.detail;

/** /skins/[id]: 3D on the left, download and library actions on the right. */
export async function SkinDetail({ id }: { id: number }) {
  const skin = Number.isSafeInteger(id) && id > 0 ? await getSkin(id) : null;
  if (!skin) notFound();
  const published = skin.status === "published";
  const similar = published ? await getSimilar(skin.id) : [];
  const identifier = String(skin.id);

  return (
    <div className="flex flex-col">
      {!published && (
        <p role="status" className="border-b border-line bg-surface px-4 py-3 text-center text-sm">
          {skin.status === "rejected" ? copy.rejected(skin.rejection_reason) : copy.pending}
        </p>
      )}
      <DetailPage
        media={
          <SkinViewer
            texture={skin.texture_url}
            model={skin.model}
            title={skin.title}
            fallback={skin.preview_url}
          />
        }
        eyebrow={<Chip tone="skins">{skinsCopy.label}</Chip>}
        title={skin.title}
        description={skin.style_tags.map((style) => skinsCopy.styles[style]).join(" · ")}
        meta={
          <>
            {copy.by}{" "}
            <Link
              href={`/u/${skin.author.nickname}`}
              className="text-text underline underline-offset-4"
            >
              {skin.author.nickname}
            </Link>
            {` · ${skinsCopy.models[skin.model]} · ${skinsCopy.colors[skin.color_bucket]} · ⬇ ${formatCount(skin.downloads_count)}`}
          </>
        }
        primaryAction={
          <a href={downloadUrl(skin.id)} download className={buttonClasses({ size: "lg" })}>
            <Icon name="download" />
            {copy.download}
          </a>
        }
        secondaryActions={
          <>
            {published && (
              <>
                <SaveToggle
                  kind="skin"
                  id={identifier}
                  saved={skin.is_favorited}
                  count={skin.favorites_count}
                  className="h-12"
                />
                <AddToCollection kind="skin" id={identifier} />
                <LikeButton
                  kind="skin"
                  id={identifier}
                  liked={skin.is_liked}
                  count={skin.likes_count}
                />
              </>
            )}
            {skin.is_mine && <SkinOwnerActions skin={skin} />}
          </>
        }
        tabsLabel={copy.tabsLabel}
        tabs={[
          {
            value: "install",
            label: copy.tabs.install,
            content: <HowToInstall model={skin.model} />,
          },
          ...(published
            ? [
                {
                  value: "comments",
                  label: skin.comments_count
                    ? `${copy.tabs.comments} · ${skin.comments_count}`
                    : copy.tabs.comments,
                  content: <Comments kind="skin" id={identifier} />,
                },
                {
                  value: "similar",
                  label: copy.tabs.similar,
                  content: similar.length ? (
                    <CardGrid>
                      {similar.map((item) => (
                        <SkinCard key={item.id} skin={item} />
                      ))}
                    </CardGrid>
                  ) : (
                    <p className="text-muted">{copy.noSimilar}</p>
                  ),
                },
              ]
            : []),
        ]}
      />
    </div>
  );
}
