import Link from "next/link";
import type { ReactNode } from "react";

import { buttonClasses } from "./buttonClasses";
import { Icon, type IconName } from "./Icon";

type TakeButtonProps = {
  href: string;
  /** Says what and for which game: «Завантажити для 1.21.1 · Fabric». */
  children: ReactNode;
  icon?: IconName;
  /** API endpoints that redirect to a file: a plain <a>, not client navigation. */
  external?: boolean;
  /** Nothing fits «Моя гра»: the fallback («Найближча версія: 1.21.11») is secondary. */
  fallback?: boolean;
};

/** The one primary «take» action of an object page (design-system: TakeButton). */
export function TakeButton({
  href,
  children,
  icon = "download",
  external = false,
  fallback = false,
}: TakeButtonProps) {
  const className = buttonClasses({
    variant: fallback ? "secondary" : "primary",
    size: "lg",
    className: "w-full sm:w-auto",
  });
  const content = (
    <>
      <Icon name={icon} />
      {children}
    </>
  );
  if (external) {
    return (
      <a href={href} className={className}>
        {content}
      </a>
    );
  }
  return (
    <Link href={href} className={className} scroll={false}>
      {content}
    </Link>
  );
}
