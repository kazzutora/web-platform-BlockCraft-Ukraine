"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

import { Button } from "@/components/ui/Button";
import { ChoiceChips } from "@/components/ui/ChoiceChips";
import { Icon } from "@/components/ui/Icon";
import { Popover } from "@/components/ui/Popover";
import { Select } from "@/components/ui/Select";
import { useToast } from "@/components/ui/useToast";
import { api } from "@/lib/api/client";
import { queryKeys } from "@/lib/query-keys";

import type { GameContext } from "./context";
import { type MyGame, saveGameCookie } from "./cookie";
import { gameCopy } from "./copy";
import { type Loader, loaderOptions } from "./labels";
import { useGameVersions } from "./useGameVersions";

const copy = gameCopy.chip;

function loaderLabel(loader: string): string {
  return loaderOptions.find((option) => option.value === loader)?.label ?? "";
}

export function gameLabel({ game_version, loader }: MyGame): string {
  return [game_version, loaderLabel(loader)].filter(Boolean).join(" · ");
}

type GameChipProps = { initial: GameContext; signedIn: boolean };

/** «1.21.1 · Fabric ▾» in the header: the game every catalog is filtered for. */
export function GameChip({ initial, signedIn }: GameChipProps) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const toast = useToast();
  const versions = useGameVersions();
  const [open, setOpen] = useState(false);
  const [howTo, setHowTo] = useState(false);
  const [saving, setSaving] = useState(false);
  const [refreshing, startRefresh] = useTransition();
  const [draft, setDraft] = useState<MyGame>({
    game_version: initial.game_version,
    loader: initial.loader,
  });
  const current = gameLabel(initial);

  async function save(game: MyGame) {
    setSaving(true);
    try {
      if (signedIn) {
        const { error } = await api.PUT("/api/v1/me/game", {
          body: { game_version: game.game_version, loader: game.loader as Loader | "" },
        });
        if (error) throw error;
        await queryClient.invalidateQueries({ queryKey: queryKeys.me.all });
      }
      // Guests keep it in the cookie; players too, so it survives signing out
      saveGameCookie(game);
      setOpen(false);
      startRefresh(() => router.refresh());
    } catch {
      toast({ title: copy.error, tone: "danger" });
    } finally {
      setSaving(false);
    }
  }

  return (
    <Popover
      label={copy.title}
      align="end"
      open={open}
      onOpenChange={(next) => {
        setOpen(next);
        if (next) setDraft({ game_version: initial.game_version, loader: initial.loader });
      }}
      trigger={
        <button
          type="button"
          aria-label={current ? copy.label(current) : copy.empty}
          aria-busy={refreshing}
          className="inline-flex h-9 max-w-32 items-center gap-1.5 border border-line px-2 text-meta font-medium whitespace-nowrap tabular-nums transition-colors hover:border-text focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent sm:max-w-none"
        >
          <span
            aria-hidden
            className={current ? "size-2 bg-accent" : "size-2 border border-muted"}
          />
          {/* Phones show the version only: the header has no room for both */}
          <span className="truncate">
            {initial.game_version ? (
              <>
                {initial.game_version}
                {initial.loader && (
                  <span className="hidden sm:inline"> · {loaderLabel(initial.loader)}</span>
                )}
              </>
            ) : (
              loaderLabel(initial.loader) || copy.empty
            )}
          </span>
          <Icon name="chevron-down" className="size-4 shrink-0" />
        </button>
      }
    >
      <div className="flex flex-col gap-4">
        <div className="flex flex-col gap-1">
          <p className="font-serif text-2xl leading-tight">{copy.title}</p>
          <p className="text-sm text-muted">{copy.intro}</p>
        </div>
        <Select
          label={copy.version}
          placeholder={copy.anyVersion}
          options={versions.map((version) => ({ value: version, label: version }))}
          value={draft.game_version}
          onChange={(event) => setDraft({ ...draft, game_version: event.target.value })}
        />
        <div className="flex flex-col gap-1">
          <button
            type="button"
            aria-expanded={howTo}
            onClick={() => setHowTo(!howTo)}
            className="self-start text-sm underline underline-offset-4"
          >
            {copy.howTo}
          </button>
          {howTo && <p className="text-sm text-muted">{copy.howToText}</p>}
        </div>
        <ChoiceChips
          label={copy.loader}
          options={loaderOptions}
          value={draft.loader as Loader | ""}
          onChange={(loader) => setDraft({ ...draft, loader })}
        />
        <div className="flex items-center gap-2">
          <Button onClick={() => save(draft)} disabled={saving} className="flex-1">
            {copy.apply}
          </Button>
          {(initial.game_version || initial.loader) && (
            <Button
              variant="ghost"
              disabled={saving}
              onClick={() => save({ game_version: "", loader: "" })}
            >
              {copy.reset}
            </Button>
          )}
        </div>
      </div>
    </Popover>
  );
}
