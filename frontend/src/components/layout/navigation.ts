import type { IconName } from "@/components/ui/Icon";

export type NavItem = { href: string; label: string };
export type TabBarItem = NavItem & { icon: IconName };

/** Sections in the header (MVP). Packs, moments and worlds join after the MVP. */
export const sections: NavItem[] = [
  { href: "/mods", label: "Моди" },
  { href: "/skins", label: "Скіни" },
  { href: "/servers", label: "Сервери" },
];

/** Bottom bar on phones. */
export const tabBar: TabBarItem[] = [
  { href: "/", label: "Головна", icon: "home" },
  { href: "/search", label: "Пошук", icon: "search" },
  { href: "/create", label: "Додати", icon: "plus" },
  { href: "/me/saved", label: "Обране", icon: "bookmark" },
];

export function isActive(pathname: string, href: string): boolean {
  return href === "/" ? pathname === "/" : pathname === href || pathname.startsWith(`${href}/`);
}
