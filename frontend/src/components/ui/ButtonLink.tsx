import Link from "next/link";
import type { ComponentProps } from "react";

import { type ButtonSize, type ButtonVariant, buttonClasses } from "./buttonClasses";

type ButtonLinkProps = ComponentProps<typeof Link> & {
  variant?: ButtonVariant;
  size?: ButtonSize;
};

/** A link that looks like a button: navigation stays a real <a>. */
export function ButtonLink({ variant, size, className, ...props }: ButtonLinkProps) {
  return <Link className={buttonClasses({ variant, size, className })} {...props} />;
}
