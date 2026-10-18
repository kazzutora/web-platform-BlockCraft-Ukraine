"use client";

import { usePathname } from "next/navigation";

import { TabBarLinks } from "./TabBarLinks";

/** Tab bar with the current item marked; render inside <Suspense fallback={<TabBarLinks />}>. */
export function MobileTabBar() {
  return <TabBarLinks pathname={usePathname()} />;
}
