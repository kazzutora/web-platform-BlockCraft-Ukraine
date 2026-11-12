"use client";

import { useMutation } from "@tanstack/react-query";
import Link from "next/link";
import { type ChangeEvent, type FormEvent, type ReactNode, useId, useState } from "react";

import { Button } from "@/components/ui/Button";
import { ButtonLink } from "@/components/ui/ButtonLink";
import { EmptyState } from "@/components/ui/EmptyState";
import { Icon } from "@/components/ui/Icon";
import { Textarea } from "@/components/ui/Textarea";
import { api } from "@/lib/api/client";
import { generalError } from "@/lib/api/errors";
import type { components } from "@/lib/api/schema";

import { helpCopy, loaderTitle } from "./copy";
import {
  type CrashReport,
  LOG_HEAD,
  MAX_LOG,
  type ModRef,
  modsOf,
  parseCrashLog,
  type Problem,
  problemsOf,
  outsideRange,
  readableRange,
} from "./crash/parse";

type Crash = components["schemas"]["CrashResponse"];
type Card = components["schemas"]["ProjectCard"];
type PackLoader = components["schemas"]["PackLoaderEnum"];

const copy = helpCopy.crash;
const MOD_LOADERS = new Set(["fabric", "quilt", "forge", "neoforge"]);

function name(mod: ModRef): string {
  return mod.name || mod.id;
}

/** The game of the log: the mod page opens its files for it, not for «Моя гра». */
type LogGame = { gameVersion: string; loader: string };

function modHref(slug: string, game?: LogGame): string {
  const query = new URLSearchParams();
  if (game?.gameVersion) query.set("game_version", game.gameVersion);
  if (game?.loader && MOD_LOADERS.has(game.loader)) query.set("loader", game.loader);
  const search = query.toString();
  return `/mods/${slug}${search ? `?${search}` : ""}`;
}

/** «Взяти Fabric API» to the catalog page, or a search when we do not have it. */
function ModLink({
  mod,
  project,
  label,
  game,
}: {
  mod: ModRef;
  project?: Card | null;
  label?: string;
  game?: LogGame;
}) {
  if (project) {
    return (
      <ButtonLink href={modHref(project.slug, game)} variant="secondary">
        {label ?? copy.actions.open(project.title)}
        <Icon name="chevron-right" size={16} />
      </ButtonLink>
    );
  }
  // A long mod id must wrap on a phone: a plain link, not a one-line button
  return (
    <p className="text-sm break-words">
      <Link
        href={`/search?q=${encodeURIComponent(name(mod))}`}
        className="font-medium underline underline-offset-4"
      >
        {copy.actions.search(name(mod))}
      </Link>{" "}
      <span className="text-muted">· {copy.notInCatalog}</span>
    </p>
  );
}

function ProblemRow({ finding, crash, game }: { finding: Problem; crash?: Crash; game: LogGame }) {
  const project = (mod: ModRef) => crash?.mods.find((row) => row.id === mod.id)?.project;
  const text = copy.findings;
  let message: string;
  let hint = "";
  let actions: ReactNode = null;

  switch (finding.type) {
    case "missing": {
      const range = finding.range ? readableRange(finding.range) : "";
      const needs = project(finding.needs);
      const needsName = needs?.title ?? name(finding.needs);
      message =
        finding.mods.length === 1
          ? text.missing(name(finding.mods[0]), needsName, range)
          : text.missingMany(needsName, range, finding.mods.map(name));
      actions = (
        <ModLink
          mod={finding.needs}
          project={needs}
          label={needs ? copy.actions.get(needs.title) : undefined}
          game={game}
        />
      );
      break;
    }
    case "wrong_game": {
      message = text.wrongGame(name(finding.mod), readableRange(finding.expected), finding.actual);
      const found = project(finding.mod);
      actions = (
        <ModLink
          mod={finding.mod}
          project={found}
          game={{ gameVersion: finding.actual, loader: game.loader }}
          label={found ? copy.actions.forGame(found.title, finding.actual) : undefined}
        />
      );
      break;
    }
    case "wrong_loader": {
      const loader = loaderTitle(finding.loader);
      message = text.wrongLoader(
        name(finding.mod),
        loader,
        readableRange(finding.expected),
        finding.actual,
      );
      if (outsideRange(finding.actual, finding.expected) === "above") {
        // The loader is newer than the mod allows: the mod is what to change
        hint = text.loaderTooNew(loader);
        actions = <ModLink mod={finding.mod} project={project(finding.mod)} game={game} />;
      } else {
        const release = crash?.loader_release;
        hint =
          release && release.version !== finding.actual
            ? copy.actions.latestLoader(loader, release.game_version, release.version)
            : text.loaderTooOld(loader);
      }
      break;
    }
    case "wrong_dependency":
      message = text.wrongDependency(
        name(finding.mod),
        name(finding.needs),
        readableRange(finding.expected),
        finding.actual,
      );
      hint = finding.optional ? text.optional : "";
      actions = <ModLink mod={finding.needs} project={project(finding.needs)} game={game} />;
      break;
    case "incompatible":
      message = text.incompatible(
        [name(finding.mod), finding.mod.version].filter(Boolean).join(" "),
        [name(finding.other), finding.other.version].filter(Boolean).join(" "),
      );
      hint = text.incompatibleHint;
      actions = (
        <>
          <ModLink mod={finding.mod} project={project(finding.mod)} />
          <ModLink mod={finding.other} project={project(finding.other)} />
        </>
      );
      break;
    case "duplicate":
      message = text.duplicate(finding.id);
      hint = text.duplicateHint;
      actions = (
        <ul className="flex flex-col gap-1 font-mono text-meta">
          {finding.files.map((file) => (
            <li key={file}>{file}</li>
          ))}
        </ul>
      );
      break;
    case "java":
      message = text.java(finding.required, finding.current);
      hint = text.javaHint(finding.required);
      break;
  }

  return (
    <li className="flex gap-4 border-b border-line py-5">
      <span aria-hidden className="mt-2 size-2 shrink-0 bg-danger" />
      <div className="flex min-w-0 flex-col gap-3">
        <p className="font-medium break-words">{message}</p>
        {hint && <p className="text-sm text-muted">{hint}</p>}
        {actions && <div className="flex flex-wrap items-center gap-3">{actions}</div>}
      </div>
    </li>
  );
}

/** /help/crash: paste a log, see what broke and what to take to fix it. */
export function CrashChecker() {
  const fileId = useId();
  const [text, setText] = useState("");
  const [report, setReport] = useState<CrashReport | null>(null);

  const lookup = useMutation({
    mutationFn: async (found: CrashReport): Promise<Crash> => {
      const { data, error } = await api.POST("/api/v1/help/crash", {
        body: {
          mods: modsOf(found)
            .slice(0, 100)
            .map((mod) => ({ id: mod.id.slice(0, 64), name: (mod.name ?? "").slice(0, 120) })),
          game_version: found.gameVersion.slice(0, 32),
          loader: MOD_LOADERS.has(found.loader) ? (found.loader as PackLoader) : "",
        },
      });
      if (!data) throw error;
      return data;
    },
  });

  function check(event: FormEvent) {
    event.preventDefault();
    const found = parseCrashLog(text);
    setReport(found);
    lookup.reset();
    if (found.findings.length) lookup.mutate(found);
  }

  async function openFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    // Read here, in the browser: the file is never uploaded. A huge log — its head (the game,
    // the loader) and its tail (the error), without reading the middle into memory
    const content =
      file.size > MAX_LOG
        ? [
            await file.slice(0, LOG_HEAD).text(),
            await file.slice(-(MAX_LOG - LOG_HEAD)).text(),
          ].join("\n")
        : await file.text();
    setText(content);
    event.target.value = "";
  }

  const problems = report ? problemsOf(report) : [];
  const context = report
    ? copy.context(loaderTitle(report.loader), report.loaderVersion, report.gameVersion)
    : "";

  return (
    <div className="flex flex-col gap-10">
      <form onSubmit={check} className="flex flex-col gap-4">
        <Textarea
          label={copy.label}
          hint={copy.where}
          rows={10}
          value={text}
          placeholder={copy.placeholder}
          spellCheck={false}
          className="font-mono text-meta"
          onChange={(event) => setText(event.target.value)}
        />
        <div className="flex flex-wrap items-center gap-4">
          <Button type="submit" size="lg" disabled={!text.trim()}>
            {copy.submit}
          </Button>
          <label
            htmlFor={fileId}
            className="inline-flex min-h-11 cursor-pointer items-center gap-2 text-sm underline-offset-4 hover:underline focus-within:outline-2 focus-within:outline-accent"
          >
            <Icon name="upload" size={16} />
            {copy.file}
            <input
              id={fileId}
              type="file"
              accept=".log,.txt,text/plain"
              className="sr-only"
              onChange={openFile}
            />
          </label>
        </div>
      </form>

      {report && (
        <section aria-live="polite" className="flex flex-col gap-4">
          {report.findings.length ? (
            <>
              <h2 className="text-h2">{copy.summary(problems.length, context)}</h2>
              {lookup.isPending && <p className="text-muted">{copy.checking}</p>}
              {lookup.isError && (
                <p className="text-danger">{generalError(lookup.error, copy.error)}</p>
              )}
              <ul className="flex flex-col border-t border-line">
                {problems.map((problem, index) => (
                  <ProblemRow
                    key={index}
                    finding={problem}
                    crash={lookup.data}
                    game={{ gameVersion: report.gameVersion, loader: report.loader }}
                  />
                ))}
              </ul>
            </>
          ) : (
            <div className="flex flex-col gap-4">
              <EmptyState title={copy.nothing} illustration="void" />
              <p className="max-w-prose text-muted">{copy.nothingHint}</p>
              {report.firstError && (
                <div className="flex flex-col gap-2">
                  <span className="caps text-muted">{copy.firstError}</span>
                  <code className="block overflow-x-auto border border-line bg-surface p-4 font-mono text-meta">
                    {report.firstError}
                  </code>
                </div>
              )}
            </div>
          )}
        </section>
      )}
    </div>
  );
}
