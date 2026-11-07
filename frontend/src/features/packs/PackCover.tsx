import Image from "next/image";

import { Illustration } from "@/components/ui/Illustration";
import { cn } from "@/lib/cn";

import type { PackIcon } from "./types";

type PackCoverProps = {
  coverUrl: string | null;
  icons: PackIcon[];
  eager?: boolean;
  className?: string;
};

/** The author's cover, else a 3×3 «inventory» of the first mod icons. */
export function PackCover({ coverUrl, icons, eager = false, className }: PackCoverProps) {
  if (coverUrl) {
    // Official packs show the Modrinth icon; covers uploaded here are 1200×630 photos
    const icon = coverUrl.startsWith("https://");
    return (
      <Image
        src={coverUrl}
        alt=""
        fill
        unoptimized={!icon}
        loading={eager ? "eager" : "lazy"}
        sizes="(min-width: 1024px) 25vw, (min-width: 768px) 33vw, 50vw"
        className={cn(icon ? "object-contain p-[18%]" : "object-cover", className)}
      />
    );
  }
  const slots = icons.filter((item) => item.icon_url).slice(0, 9);
  if (!slots.length) {
    return (
      <div className={cn("flex size-full items-center justify-center", className)}>
        <Illustration name="packs" size={96} />
      </div>
    );
  }
  return (
    <div className={cn("grid size-full grid-cols-3 gap-1 p-[10%]", className)}>
      {Array.from({ length: 9 }, (_, index) => {
        const item = slots[index];
        return (
          <div key={index} className="relative aspect-square border border-line bg-bg">
            {item?.icon_url && (
              <Image
                src={item.icon_url}
                alt=""
                fill
                sizes="64px"
                loading={eager ? "eager" : "lazy"}
                className="object-contain p-1"
              />
            )}
          </div>
        );
      })}
    </div>
  );
}
