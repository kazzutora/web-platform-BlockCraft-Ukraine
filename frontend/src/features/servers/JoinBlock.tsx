import { CompatStatus } from "@/components/ui/CompatStatus";
import { TakeButton } from "@/components/ui/TakeButton";
import { PackCard } from "@/features/packs/PackCard";

import { serversCopy } from "./copy";
import type { Join } from "./types";

const copy = serversCopy.join;

/**
 * «Щоб зайти»: a version for vanilla servers, the pack to take for modded ones; whether
 * «Моя гра» already fits. For a modded server «Взяти збірку» is the page's main action.
 */
export function JoinBlock({ join, gameLabel }: { join: Join; gameLabel: string }) {
  return (
    <section
      aria-labelledby="join-title"
      className="flex flex-col gap-6 border border-line p-6 md:p-8"
    >
      <h2 id="join-title" className="caps font-sans">
        {copy.title}
      </h2>
      {join.kind === "modded" ? (
        <Modded join={join} />
      ) : (
        <Vanilla join={join} gameLabel={gameLabel} />
      )}
    </section>
  );
}

function Vanilla({ join, gameLabel }: { join: Join; gameLabel: string }) {
  const version = join.recommended_version || join.versions[0] || "";
  const others = join.versions.filter((item) => item !== version);
  return (
    <div className="flex flex-col gap-3">
      <p className="font-serif text-h2">{version ? copy.version(version) : copy.anyVersion}</p>
      {others.length > 0 && (
        <p className="text-meta text-muted">{copy.versions(join.versions.join(", "))}</p>
      )}
      {join.fits_my_game === true && <CompatStatus tone="ok">{copy.fits}</CompatStatus>}
      {join.fits_my_game === false && (
        <CompatStatus tone="warning">{copy.notFits(gameLabel)}</CompatStatus>
      )}
      <p className="text-sm text-muted">{copy.howTo}</p>
    </div>
  );
}

function Modded({ join }: { join: Join }) {
  if (!join.pack) {
    return <p className="max-w-prose">{join.pack_pending ? copy.packPending : copy.packMissing}</p>;
  }
  return (
    <div className="grid gap-6 sm:grid-cols-[160px_minmax(0,1fr)] sm:items-start">
      <div className="w-40">
        <PackCard pack={join.pack} />
      </div>
      <div className="flex flex-col items-start gap-4">
        <p className="font-serif text-h2">{copy.pack}</p>
        {join.fits_my_game === false && (
          <CompatStatus tone="warning">{copy.notFitsPack}</CompatStatus>
        )}
        <TakeButton href={`/packs/${join.pack.slug}`} icon="download">
          {copy.takePack}
        </TakeButton>
        <p className="text-sm text-muted">{copy.howTo}</p>
      </div>
    </div>
  );
}
