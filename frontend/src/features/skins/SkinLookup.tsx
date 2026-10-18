"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { type FormEvent, useState } from "react";

import { Button } from "@/components/ui/Button";
import { buttonClasses } from "@/components/ui/buttonClasses";
import { EmptyState } from "@/components/ui/EmptyState";
import { Icon } from "@/components/ui/Icon";
import { Input } from "@/components/ui/Input";
import { Skeleton } from "@/components/ui/Skeleton";

import { skinsCopy } from "./copy";
import { SkinViewer } from "./SkinViewer";
import { LookupError, NICKNAME, usePlayerSkin } from "./usePlayerSkin";

const copy = skinsCopy.lookupPage;

/** /skins/lookup: the nickname lives in the URL, so a result can be shared. */
export function SkinLookup() {
  const router = useRouter();
  const pathname = usePathname();
  const nickname = useSearchParams().get("nickname") ?? "";
  const [value, setValue] = useState(nickname);
  const [error, setError] = useState("");
  const player = usePlayerSkin(nickname);

  function submit(event: FormEvent) {
    event.preventDefault();
    const next = value.trim();
    if (!NICKNAME.test(next)) {
      setError(copy.invalid);
      return;
    }
    setError("");
    router.replace(`${pathname}?nickname=${encodeURIComponent(next)}`, { scroll: false });
  }

  const status = player.error instanceof LookupError ? player.error.status : 0;

  return (
    <div className="flex flex-col gap-10">
      <form onSubmit={submit} noValidate className="flex flex-col gap-3 sm:flex-row sm:items-start">
        <div className="sm:w-80">
          <Input
            label={copy.nickname}
            hideLabel
            placeholder={copy.nickname}
            autoComplete="off"
            spellCheck={false}
            maxLength={16}
            value={value}
            onChange={(event) => setValue(event.target.value)}
            error={error}
          />
        </div>
        <Button type="submit" size="lg">
          <Icon name="search" />
          {copy.submit}
        </Button>
      </form>

      {nickname && player.isPending && player.fetchStatus !== "idle" && (
        <Skeleton className="aspect-square w-full max-w-md" />
      )}

      {player.isError && (
        <EmptyState
          illustration={status === 404 ? "void" : "error"}
          title={status === 404 ? copy.notFound : copy.busy}
        />
      )}

      {player.data &&
        (player.data.texture && player.data.model ? (
          <div className="grid gap-10 md:grid-cols-2 md:gap-16">
            <div className="relative aspect-square border border-line bg-surface">
              <SkinViewer
                texture={player.data.texture}
                model={player.data.model}
                title={player.data.nickname}
              />
            </div>
            <div className="flex flex-col gap-6 md:justify-center">
              <h2 className="text-h2">{player.data.nickname}</h2>
              <p className="text-meta text-muted">{skinsCopy.models[player.data.model]}</p>
              <a
                href={player.data.texture}
                download={`${player.data.nickname}.png`}
                className={buttonClasses({ size: "lg", className: "self-start" })}
              >
                <Icon name="download" />
                {skinsCopy.detail.download}
              </a>
              <p className="max-w-prose text-meta text-muted">{copy.hint}</p>
            </div>
          </div>
        ) : (
          <EmptyState illustration="skins" title={copy.defaultSkin(player.data.nickname)} />
        ))}
    </div>
  );
}
