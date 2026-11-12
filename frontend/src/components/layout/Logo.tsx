import Link from "next/link";

const copy = { name: "BlockCraft", home: "BlockCraft — на головну" };

/** Wordmark: a grass-green square and the name in the display face (Unbounded is wide: smaller on phones). */
export function Logo() {
  return (
    <Link href="/" aria-label={copy.home} className="inline-flex shrink-0 items-center gap-2">
      <span aria-hidden className="size-3 bg-accent" />
      <span className="font-display text-base leading-none font-semibold tracking-tight md:text-xl">
        {copy.name}
      </span>
    </Link>
  );
}
