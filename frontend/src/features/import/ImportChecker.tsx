"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { type ChangeEvent, type DragEvent, useRef, useState } from "react";

import { Button } from "@/components/ui/Button";
import { ChoiceChips } from "@/components/ui/ChoiceChips";
import { CompatStatus } from "@/components/ui/CompatStatus";
import { Icon } from "@/components/ui/Icon";
import { Select } from "@/components/ui/Select";
import { Skeleton } from "@/components/ui/Skeleton";
import { useToast } from "@/components/ui/useToast";
import { useRequireAuth } from "@/features/auth/useRequireAuth";
import { ResolutionView, targetLabel } from "@/features/compat/ResolutionView";
import { useGameVersions } from "@/features/game/useGameVersions";
import { packsCopy } from "@/features/packs/copy";
import { type PackLoader, packLoaders } from "@/features/packs/types";
import { api } from "@/lib/api/client";
import { generalError } from "@/lib/api/errors";
import { plural } from "@/lib/plural";
import { queryKeys } from "@/lib/query-keys";
import { cn } from "@/lib/cn";

import { importCopy as copy } from "./copy";
import {
  type MrpackIndex,
  NotAModpack,
  hashAll,
  indexFiles,
  isModFile,
  readMrpackIndex,
} from "./files";
import type { Identified, Target } from "./types";

type Hashed = { hash: string; name: string };
/** What one check takes (the API limit); a bigger folder is checked in part. */
const MAX_FILES = 2000;
type State =
  | { step: "idle" }
  | { step: "hashing"; done: number; total: number }
  | { step: "asking" }
  | { step: "report"; files: Hashed[]; result: Identified; index: MrpackIndex | null }
  | { step: "error"; message: string };

const LOADER_KEYS: Record<string, PackLoader> = {
  "fabric-loader": "fabric",
  "quilt-loader": "quilt",
  forge: "forge",
  neoforge: "neoforge",
};

function indexTarget(index: MrpackIndex | null): Target | null {
  const game = index?.dependencies?.minecraft;
  const key = Object.keys(index?.dependencies ?? {}).find((name) => name in LOADER_KEYS);
  return game && key ? { game_version: game, loader: LOADER_KEYS[key] } : null;
}

/** /import: a folder or a .mrpack in, a report out; files never leave the browser. */
export function ImportChecker() {
  const [state, setState] = useState<State>({ step: "idle" });
  const folderInput = useRef<HTMLInputElement>(null);
  const filesInput = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  async function check(list: File[]) {
    try {
      const modpack = list.find((file) => file.name.toLowerCase().endsWith(".mrpack"));
      let files: Hashed[];
      let index: MrpackIndex | null = null;
      if (modpack) {
        index = (await readMrpackIndex(modpack)) as MrpackIndex;
        files = indexFiles(index);
      } else {
        const mods = list.filter(isModFile);
        if (!mods.length) {
          setState({ step: "error", message: copy.noFiles });
          return;
        }
        setState({ step: "hashing", done: 0, total: mods.length });
        files = await hashAll(mods, (done) =>
          setState({ step: "hashing", done, total: mods.length }),
        );
      }
      setState({ step: "asking" });
      const { data, error } = await api.POST("/api/v1/compat/identify", {
        body: { algorithm: "sha1", files: files.slice(0, MAX_FILES) },
      });
      if (!data) throw error;
      setState({ step: "report", files, result: data, index });
    } catch (error) {
      setState({
        step: "error",
        message: error instanceof NotAModpack ? copy.notModpack : generalError(error, copy.error),
      });
    }
  }

  function pick(event: ChangeEvent<HTMLInputElement>) {
    const list = Array.from(event.target.files ?? []);
    event.target.value = "";
    if (list.length) void check(list);
  }

  async function drop(event: DragEvent) {
    event.preventDefault();
    setDragging(false);
    void check(await droppedFiles(event.dataTransfer));
  }

  if (state.step === "report") {
    return (
      <Report
        files={state.files}
        result={state.result}
        index={state.index}
        onAgain={() => setState({ step: "idle" })}
      />
    );
  }

  const busy = state.step === "hashing" || state.step === "asking";
  return (
    <div className="flex flex-col gap-6">
      <div
        onDragOver={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(event) => void drop(event)}
        className={cn(
          "flex min-h-64 flex-col items-center justify-center gap-6 border border-dashed p-8 text-center",
          dragging ? "border-text bg-surface" : "border-line",
        )}
      >
        <Icon name="download" size={48} />
        <p className="max-w-md text-lg">{copy.drop}</p>
        <div className="flex flex-col gap-3 sm:flex-row">
          <Button size="lg" disabled={busy} onClick={() => folderInput.current?.click()}>
            {copy.chooseFolder}
          </Button>
          <Button
            variant="secondary"
            size="lg"
            disabled={busy}
            onClick={() => filesInput.current?.click()}
          >
            {copy.chooseFiles}
          </Button>
        </div>
        <input
          ref={folderInput}
          type="file"
          className="sr-only"
          tabIndex={-1}
          multiple
          onChange={pick}
          {...{ webkitdirectory: "" }}
        />
        <input
          ref={filesInput}
          type="file"
          className="sr-only"
          tabIndex={-1}
          multiple
          accept=".jar,.zip,.mrpack"
          onChange={pick}
        />
      </div>
      <p role="status" aria-live="polite" className="text-meta text-muted">
        {state.step === "hashing" && copy.hashing(state.done, state.total)}
        {state.step === "asking" && copy.asking}
        {state.step === "error" && <span className="text-danger">{state.message}</span>}
      </p>
    </div>
  );
}

/** Files of a dropped folder: the browser hands over entries, not files. */
async function droppedFiles(transfer: DataTransfer): Promise<File[]> {
  const entries = Array.from(transfer.items)
    .map((item) => item.webkitGetAsEntry?.())
    .filter((entry): entry is FileSystemEntry => Boolean(entry));
  if (!entries.length) return Array.from(transfer.files);
  const files: File[] = [];
  async function walk(entry: FileSystemEntry): Promise<void> {
    if (entry.isFile) {
      files.push(
        await new Promise((resolve, reject) =>
          (entry as FileSystemFileEntry).file(resolve, reject),
        ),
      );
      return;
    }
    const reader = (entry as FileSystemDirectoryEntry).createReader();
    let batch: FileSystemEntry[];
    do {
      batch = await new Promise((resolve, reject) => reader.readEntries(resolve, reject));
      for (const child of batch) await walk(child);
    } while (batch.length);
  }
  for (const entry of entries) await walk(entry);
  return files;
}

type ReportProps = {
  files: Hashed[];
  result: Identified;
  index: MrpackIndex | null;
  onAgain: () => void;
};

function Report({ files, result, index, onAgain }: ReportProps) {
  const own = indexTarget(index) ?? result.guess;
  const versions = useGameVersions();
  const [other, setOther] = useState<Target | null>(null);
  const [draftTarget, setDraftTarget] = useState<Target>(
    own ?? { game_version: versions[0] ?? "", loader: "fabric" },
  );
  const router = useRouter();
  const toast = useToast();
  const requireAuth = useRequireAuth();
  const known = result.known;

  const check = useQuery({
    queryKey: queryKeys.imports.check(
      own,
      known.map((item) => item.version.id),
    ),
    enabled: Boolean(own) && known.length > 0,
    queryFn: async () => {
      const { data, error } = await api.POST("/api/v1/compat/resolve", {
        body: {
          game_version: own?.game_version ?? "",
          loader: (own?.loader ?? "fabric") as PackLoader,
          items: known.slice(0, 300).map((item) => ({
            slug: item.project.slug,
            version_id: item.version.id,
          })),
        },
      });
      if (!data) throw error;
      return data;
    },
  });

  const updates = useQuery({
    queryKey: queryKeys.imports.updates(
      other,
      known.map((item) => item.hash),
    ),
    enabled: Boolean(other) && known.length > 0,
    queryFn: async () => {
      const { data, error } = await api.POST("/api/v1/compat/updates", {
        body: {
          algorithm: "sha1",
          files: known.map((item) => ({ hash: item.hash, name: item.name })),
          game_version: other?.game_version ?? "",
          loader: (other?.loader ?? "fabric") as PackLoader,
        },
      });
      if (!data) throw error;
      return data;
    },
  });

  const save = useMutation({
    mutationFn: async () => {
      // Without a guess, the game chosen below goes into the pack
      const target = own ?? draftTarget;
      const body = index
        ? { index: index as Record<string, unknown> }
        : {
            files: files.slice(0, MAX_FILES),
            game_version: target.game_version,
            loader: target.loader as PackLoader,
          };
      const { data, error } = await api.POST("/api/v1/packs/import", { body });
      if (!data) throw error;
      return data;
    },
    onError: (error) =>
      toast({ title: generalError(error, copy.report.saveError), tone: "danger" }),
    onSuccess: (pack) => router.push(`/packs/${pack.slug}/edit`),
  });

  return (
    <div className="flex flex-col gap-12">
      <header className="flex flex-col gap-4">
        <p className="text-meta text-muted">{plural(files.length, copy.files)}</p>
        <h2 className="font-display text-h2">
          {own ? copy.report.guess(targetLabel(own)) : copy.report.noGuess}
        </h2>
        {own && !index && result.identified > 0 && (
          <p className="text-muted">{copy.report.guessHint(result.fitting, result.identified)}</p>
        )}
        {result.source_unavailable && (
          <CompatStatus tone="warning">{copy.unavailable}</CompatStatus>
        )}
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <Button
            size="lg"
            loading={save.isPending}
            disabled={!known.length}
            onClick={() => requireAuth(() => save.mutate())}
          >
            {copy.report.save}
          </Button>
          <Button variant="ghost" size="lg" onClick={onAgain}>
            {copy.again}
          </Button>
        </div>
        <p className="text-meta text-muted">
          {own ? copy.report.saveHint : copy.report.saveNoGuess}
        </p>
        {files.length > MAX_FILES && (
          <p className="text-meta text-muted">{copy.report.tooMany(MAX_FILES)}</p>
        )}
      </header>

      {own &&
        known.length > 0 &&
        (check.isPending ? (
          <Skeleton className="h-40 w-full" />
        ) : check.data ? (
          <ResolutionView
            resolution={check.data}
            title={copy.report.check}
            mode="problems"
            live={false}
            downloads={false}
          />
        ) : null)}

      <section aria-labelledby="known-files" className="flex flex-col gap-4">
        <h2 id="known-files" className="font-display text-h2">
          {copy.report.known} · {known.length}
        </h2>
        <ul className="flex flex-col divide-y divide-line border-y border-line">
          {known.map((item) => {
            const next = updates.data?.files.find((row) => row.hash === item.hash);
            return (
              <li
                key={item.hash}
                className="flex flex-col gap-1 py-3 sm:flex-row sm:items-baseline sm:justify-between"
              >
                <span className="min-w-0">
                  <span className="font-medium">{item.project.title}</span>{" "}
                  <span className="font-mono text-meta text-muted">
                    {item.version.version_number}
                  </span>
                </span>
                {next && (
                  <span
                    className={cn(
                      "text-meta",
                      next.status === "not_ported" ? "text-danger" : "text-muted",
                    )}
                  >
                    {next.status === "update" && next.latest
                      ? copy.report.update(next.latest.version_number)
                      : next.status === "up_to_date"
                        ? copy.report.upToDate
                        : copy.report.notPorted}
                  </span>
                )}
              </li>
            );
          })}
        </ul>
      </section>

      {known.length > 0 && (
        <section aria-labelledby="other-target" className="flex flex-col gap-4">
          <h2 id="other-target" className="font-display text-h2">
            {copy.report.updates}
          </h2>
          <div className="flex flex-col gap-4 sm:flex-row sm:items-end">
            <Select
              label={copy.report.version}
              value={draftTarget.game_version}
              options={versions.map((value) => ({ value, label: value }))}
              onChange={(event) =>
                setDraftTarget({ ...draftTarget, game_version: event.target.value })
              }
            />
            <ChoiceChips
              label={copy.report.loader}
              options={packLoaders.map((value) => ({ value, label: packsCopy.loaders[value] }))}
              value={draftTarget.loader as PackLoader}
              onChange={(value) => setDraftTarget({ ...draftTarget, loader: value })}
            />
            <Button
              variant="secondary"
              size="lg"
              loading={updates.isFetching}
              onClick={() => setOther(draftTarget)}
            >
              {copy.report.showUpdates}
            </Button>
          </div>
        </section>
      )}

      {result.unknown.length > 0 && (
        <section aria-labelledby="unknown-files" className="flex flex-col gap-3">
          <h2 id="unknown-files" className="font-display text-h2">
            {copy.report.unknown} · {result.unknown.length}
          </h2>
          <p className="text-muted">{copy.report.unknownHint}</p>
          <ul className="flex flex-col gap-1 font-mono text-meta">
            {result.unknown.map((item) => (
              <li key={item.hash} className="truncate">
                {item.name || item.hash}
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
