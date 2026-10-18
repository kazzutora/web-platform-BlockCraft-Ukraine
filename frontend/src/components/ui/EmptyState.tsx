import type { ReactNode } from "react";

import { Illustration, type IllustrationName } from "./Illustration";

type EmptyStateProps = {
  /** One short phrase. */
  title: string;
  illustration?: IllustrationName;
  /** One action, e.g. a ButtonLink. */
  action?: ReactNode;
};

export function EmptyState({ title, illustration = "empty", action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center gap-6 py-16 text-center">
      <Illustration name={illustration} size={96} />
      <p className="max-w-prose text-lg">{title}</p>
      {action}
    </div>
  );
}
