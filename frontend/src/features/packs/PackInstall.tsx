import { Icon } from "@/components/ui/Icon";
import { formatFileSize } from "@/features/mods/format";

import { packsCopy } from "./copy";
import type { PackDetail, PackFile } from "./types";

const copy = packsCopy.detail.install;

type PackInstallProps = { files: PackFile[]; external: PackDetail["external_files"] };

/** «Як встановити»: three launchers in a sentence each, then every file by hand. */
export function PackInstall({ files, external }: PackInstallProps) {
  const hasDatapacks = files.some((file) => file.folder === "datapacks");
  return (
    <div className="flex max-w-3xl flex-col gap-10">
      <section className="flex flex-col gap-4">
        <ol className="flex flex-col gap-4">
          {copy.launchers.map((launcher) => (
            <li key={launcher.name} className="flex flex-col gap-1 border-t border-line pt-3">
              <span className="font-medium">{launcher.name}</span>
              <span className="text-muted">{launcher.steps}</span>
            </li>
          ))}
        </ol>
        <p className="text-meta text-muted">{copy.launcherNote}</p>
      </section>

      {files.length > 0 && (
        <section aria-labelledby="manual-install" className="flex flex-col gap-3">
          <h2 id="manual-install" className="font-serif text-h2">
            {copy.manual}
          </h2>
          <p className="text-muted">{copy.manualHint}</p>
          {hasDatapacks && (
            <p className="text-meta text-muted">{packsCopy.detail.install.datapacks}</p>
          )}
          <ul className="flex flex-col divide-y divide-line border-y border-line">
            {files.map((file) => (
              <li
                key={file.url}
                className="flex flex-col gap-1 py-3 sm:flex-row sm:items-center sm:justify-between"
              >
                <span className="min-w-0">
                  <span className="font-medium">{file.project.title}</span>{" "}
                  <span className="font-mono text-meta text-muted">{copy.folder(file.folder)}</span>
                  {file.optional && (
                    <span className="text-meta text-muted"> · {copy.optional}</span>
                  )}
                </span>
                <a
                  href={file.url}
                  rel="noopener"
                  className="inline-flex shrink-0 items-center gap-2 text-sm underline underline-offset-4"
                >
                  <Icon name="download" size={16} />
                  <span className="max-w-56 truncate">{file.file_name}</span>
                  <span className="text-muted">{formatFileSize(file.size)}</span>
                </a>
              </li>
            ))}
          </ul>
        </section>
      )}

      {external.length > 0 && (
        <section aria-labelledby="external-files" className="flex flex-col gap-3">
          <h2 id="external-files" className="font-serif text-h2">
            {packsCopy.detail.external}
          </h2>
          <p className="text-muted">{packsCopy.detail.externalHint}</p>
          <ul className="flex flex-col gap-1 font-mono text-meta">
            {external.map((file) => (
              <li key={file.path} className="truncate">
                {file.path}
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
