import { Icon } from "@/components/ui/Icon";

import { packsCopy } from "./copy";
import type { Issue } from "./types";

const copy = packsCopy.builder;

/** Warnings from the server: files missing, dependencies missing, conflicts. */
export function PackIssues({ issues }: { issues: Issue[] }) {
  if (!issues.length) return null;
  return (
    <section
      aria-labelledby="pack-issues"
      className="flex flex-col gap-4 border border-danger p-5 md:p-6"
    >
      <h2 id="pack-issues" className="flex items-center gap-2 font-medium">
        <Icon name="warning" />
        {copy.issues}
      </h2>
      <ul className="flex flex-col gap-2 text-sm">
        {issues.map((issue, index) => (
          <li key={`${issue.type}-${issue.project.slug}-${index}`}>
            <span className="font-medium">{issue.project.title}</span>
            {": "}
            {issue.message}
            {issue.other_modrinth_id && (
              <span className="text-muted"> {copy.unknownDependency}</span>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}
