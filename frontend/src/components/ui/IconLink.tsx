import Link from "next/link";
import type { ComponentProps } from "react";

import { cn } from "@/lib/cn";

import { Icon, type IconName } from "./Icon";

type IconLinkProps = Omit<ComponentProps<typeof Link>, "children"> & {
  icon: IconName;
  /** Required accessible name: the link shows only an icon. */
  label: string;
};

export function IconLink({ icon, label, className, ...props }: IconLinkProps) {
  return (
    <Link
      aria-label={label}
      title={label}
      className={cn(
        "inline-flex size-11 shrink-0 items-center justify-center text-text transition-colors duration-150 hover:bg-line",
        className,
      )}
      {...props}
    >
      <Icon name={icon} />
    </Link>
  );
}
