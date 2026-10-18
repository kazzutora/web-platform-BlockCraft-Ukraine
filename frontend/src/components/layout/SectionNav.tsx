"use client";

import { usePathname } from "next/navigation";

import { SectionLinks } from "./SectionLinks";

/**
 * Section links with the current one marked. Reads the URL, so render it inside
 * <Suspense fallback={<SectionLinks />}> (or only after user interaction).
 */
export function SectionNav(props: { vertical?: boolean; onNavigate?: () => void }) {
  return <SectionLinks pathname={usePathname()} {...props} />;
}
