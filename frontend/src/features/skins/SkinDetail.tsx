import Link from "next/link";
import { notFound } from "next/navigation";

import { DetailPage } from "@/components/layout/DetailPage";
import { CardGrid } from "@/components/ui/CardGrid";
import { Chip } from "@/components/ui/Chip";
import { SourceBadge } from "@/components/ui/SourceBadge";
import { TakeButton } from "@/components/ui/TakeButton";
import { AddToCollection } from "@/features/library/AddToCollection";
import { SaveToggle } from "@/features/library/SaveToggle";
import { formatCount } from "@/features/mods/format";
import { ReportButton } from "@/features/moderation/ReportButton";

import { downloadUrl, getSimilar, getSkin } from "./api";
import { skinsCopy } from "./copy";
import { HowToInstall } from "./HowToInstall";
import { MakeMySkin } from "./MakeMySkin";
import { SkinCard } from "./SkinCard";
import { SkinViewer } from "./SkinViewer";

const copy = skinsCopy.detail;

/** /skins/[id]: 3D on the left; «Завантажити PNG», «Зробити моїм скіном», where it is from. */
export async function SkinDetail({ id }: { id: number }) {
  const skin = Number.isSafeInteger(id) && id > 0 ? await getSkin(id) : null;
  if (!skin) notFound();
  const similar = await getSimilar(skin.id);
  const identifier = String(skin.id);

  return (
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
      description={skin.player_name ? copy.player(skin.player_name) : undefined}
      meta={
        <>
          {`${skinsCopy.models[skin.model]} · ${skinsCopy.colors[skin.color_bucket]} · ⬇ ${formatCount(skin.downloads_count)}`}
          {skin.added_by && (
            <>
              {` · ${copy.addedBy} `}
              <Link
                href={`/u/${skin.added_by.nickname}`}
                className="text-text underline underline-offset-4"
              >
                {skin.added_by.nickname}
              </Link>
            </>
          )}
          {" · "}
          <SourceBadge {...skin.source} label={copy.source(skin.title, skin.source.name)} />
        </>
      }
      primaryAction={
        <TakeButton href={downloadUrl(skin.id)} external>
          {copy.download}
        </TakeButton>
      }
      secondaryActions={
        <>
          <MakeMySkin skinId={skin.id} initial={skin.is_my_skin} />
          <SaveToggle
            kind="skin"
            id={identifier}
            saved={skin.is_favorited}
            count={skin.favorites_count}
            className="h-12"
          />
          <AddToCollection kind="skin" id={identifier} />
          <ReportButton kind="skin" id={identifier} />
        </>
      }
      tabsLabel={copy.tabsLabel}
      tabs={[
        {
          value: "install",
          label: copy.tabs.install,
          content: <HowToInstall model={skin.model} />,
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
      ]}
    />
  );
}
