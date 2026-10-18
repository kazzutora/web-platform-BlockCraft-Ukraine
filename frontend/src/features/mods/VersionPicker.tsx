"use client";

import { usePathname, useRouter } from "next/navigation";
import { useTransition } from "react";

import { Select } from "@/components/ui/Select";

import { modsCopy } from "./copy";
import { loaderName } from "./format";

const copy = modsCopy.detail;

type VersionPickerProps = {
  gameVersions: string[];
  loaders: string[];
  gameVersion: string;
  loader: string;
};

/** Changes the version and loader of the download button via the URL. */
export function VersionPicker({ gameVersions, loaders, gameVersion, loader }: VersionPickerProps) {
  const router = useRouter();
  const pathname = usePathname();
  const [pending, startTransition] = useTransition();

  function go(next: { game_version?: string; loader?: string }) {
    const params = new URLSearchParams({ game_version: gameVersion, loader, ...next });
    if (!params.get("loader")) params.delete("loader");
    startTransition(() => router.replace(`${pathname}?${params}`, { scroll: false }));
  }

  return (
    <div className="flex flex-wrap gap-3" aria-busy={pending || undefined}>
      <div className="w-36">
        <Select
          label={copy.pickerVersion}
          hideLabel
          value={gameVersion}
          options={gameVersions.map((version) => ({ value: version, label: version }))}
          onChange={(event) => go({ game_version: event.target.value })}
        />
      </div>
      {loaders.length > 0 && (
        <div className="w-36">
          <Select
            label={copy.pickerLoader}
            hideLabel
            value={loader}
            options={loaders.map((item) => ({ value: item, label: loaderName(item) }))}
            onChange={(event) => go({ loader: event.target.value })}
          />
        </div>
      )}
    </div>
  );
}
