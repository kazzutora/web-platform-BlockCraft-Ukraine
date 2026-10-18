"use client";

import Image from "next/image";
import { useState } from "react";

import { cn } from "@/lib/cn";

type GalleryProps = {
  title: string;
  iconUrl: string;
  images: Array<{ url: string; title: string }>;
};

const copy = { show: (n: number) => `Зображення ${n}` };

/** Main image with thumbnails; projects without a gallery show their icon. */
export function ModGallery({ title, iconUrl, images }: GalleryProps) {
  const [active, setActive] = useState(0);

  if (!images.length) {
    return (
      <div className="flex size-full items-center justify-center p-[25%]">
        {iconUrl && (
          <Image
            src={iconUrl}
            alt={title}
            width={256}
            height={256}
            className="size-full object-contain"
            loading="eager"
            fetchPriority="high"
          />
        )}
      </div>
    );
  }

  const current = images[Math.min(active, images.length - 1)];
  return (
    <div className="flex size-full flex-col">
      <div className="relative flex-1">
        <Image
          src={current.url}
          alt={current.title || title}
          fill
          sizes="(min-width: 768px) 50vw, 100vw"
          className="object-cover"
          loading="eager"
          fetchPriority="high"
        />
      </div>
      {images.length > 1 && (
        <div className="no-scrollbar flex gap-2 overflow-x-auto border-t border-line bg-bg p-2">
          {images.slice(0, 8).map((image, index) => (
            <button
              key={image.url}
              type="button"
              aria-label={copy.show(index + 1)}
              aria-pressed={index === active}
              onClick={() => setActive(index)}
              className={cn(
                "relative h-12 w-20 shrink-0 border",
                index === active ? "border-text" : "border-line opacity-70 hover:opacity-100",
              )}
            >
              <Image src={image.url} alt="" fill sizes="80px" className="object-cover" />
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
