import Image from "next/image";
import Link from "next/link";
import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

type CardProps = {
  href: string;
  title: string;
  /** One line of metadata: «1.21 · Fabric · ★ 4.6». */
  meta?: ReactNode;
  image?: { src: string; alt: string; pixelated?: boolean };
  /** Custom cover when there is no image (illustration, 2D skin render). */
  cover?: ReactNode;
  /** Corner action, e.g. SaveButton: shown on hover, always on touch screens. */
  action?: ReactNode;
};

export function Card({ href, title, meta, image, cover, action }: CardProps) {
  return (
    <article className="group relative flex flex-col gap-3">
      <div className="relative aspect-square overflow-hidden border border-line bg-surface">
        <div className="relative size-full transition-transform duration-200 group-hover:scale-[1.02]">
          {image ? (
            <Image
              src={image.src}
              alt={image.alt}
              fill
              sizes="(min-width: 1024px) 25vw, (min-width: 768px) 33vw, 50vw"
              className={cn("object-cover", image.pixelated && "[image-rendering:pixelated]")}
            />
          ) : (
            cover
          )}
        </div>
        {action && (
          <div className="absolute top-2 right-2 z-10 transition-opacity duration-150 can-hover:opacity-0 can-hover:group-focus-within:opacity-100 can-hover:group-hover:opacity-100">
            {action}
          </div>
        )}
      </div>
      <div className="flex flex-col gap-1">
        <h3 className="font-sans text-card font-medium">
          {/* The whole card is clickable; the corner action stays above the link */}
          <Link href={href} className="after:absolute after:inset-0">
            {title}
          </Link>
        </h3>
        {meta && <p className="text-meta text-muted">{meta}</p>}
      </div>
    </article>
  );
}
