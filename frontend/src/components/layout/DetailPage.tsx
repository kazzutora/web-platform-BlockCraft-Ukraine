import type { ReactNode } from "react";

import { type TabItem, Tabs } from "@/components/ui/Tabs";

import { Container } from "./Container";

type DetailPageProps = {
  /** Image, gallery or the 3D skin viewer. */
  media: ReactNode;
  /** Small mark above the title, e.g. a section Chip. */
  eyebrow?: ReactNode;
  title: string;
  /** Up to two lines. */
  description?: string;
  /** Metadata line: versions, loaders, rating. */
  meta?: ReactNode;
  /** The one primary action of the screen. */
  primaryAction?: ReactNode;
  /** «Зберегти», «В колекцію». */
  secondaryActions?: ReactNode;
  tabs?: TabItem[];
  tabsLabel?: string;
};

/** Object page: media on the left, info and actions on the right, tabs below. */
export function DetailPage({
  media,
  eyebrow,
  title,
  description,
  meta,
  primaryAction,
  secondaryActions,
  tabs,
  tabsLabel = "Розділи сторінки",
}: DetailPageProps) {
  return (
    <Container className="flex flex-col gap-16 py-12 md:py-16">
      <div className="grid gap-10 md:grid-cols-2 md:gap-16">
        <div className="relative aspect-square overflow-hidden border border-line bg-surface">
          {media}
        </div>
        <div className="flex flex-col gap-6 md:justify-center">
          {eyebrow && <div>{eyebrow}</div>}
          <h1 className="text-h1">{title}</h1>
          {description && <p className="line-clamp-2 max-w-prose text-muted">{description}</p>}
          {meta && <div className="text-meta text-muted">{meta}</div>}
          {(primaryAction || secondaryActions) && (
            <div className="flex flex-wrap items-center gap-3">
              {primaryAction}
              {secondaryActions}
            </div>
          )}
        </div>
      </div>
      {tabs && tabs.length > 0 && <Tabs items={tabs} label={tabsLabel} />}
    </Container>
  );
}
