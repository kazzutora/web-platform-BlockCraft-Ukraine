import Image from "next/image";

import { cn } from "@/lib/cn";

type AvatarProps = {
  name: string;
  src?: string | null;
  size?: 32 | 40 | 64 | 96 | 128;
  className?: string;
};

/** Square avatar; without an image shows the first letter of the name. */
export function Avatar({ name, src, size = 40, className }: AvatarProps) {
  return (
    <span
      className={cn(
        "relative inline-flex shrink-0 items-center justify-center overflow-hidden border border-line bg-surface font-serif",
        className,
      )}
      style={{ width: size, height: size, fontSize: size * 0.45 }}
    >
      {src ? (
        <Image src={src} alt={name} fill sizes={`${size}px`} className="object-cover" />
      ) : (
        <span role="img" aria-label={name}>
          {name.charAt(0).toUpperCase()}
        </span>
      )}
    </span>
  );
}
