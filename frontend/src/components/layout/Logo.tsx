import Link from "next/link";

const copy = { name: "BlockCraft", home: "BlockCraft — на головну" };

/** Wordmark: a grass-green square and the name in the serif face. */
export function Logo() {
  return (
    <Link href="/" aria-label={copy.home} className="inline-flex items-center gap-2">
      <span aria-hidden className="size-3 bg-accent" />
      <span className="font-serif text-2xl leading-none font-semibold">{copy.name}</span>
    </Link>
  );
}
