import type { IconName } from "@/components/ui/Icon";

export type NavItem = { href: string; label: string };
export type TabBarItem = NavItem & { icon: IconName };

/** Sections in the header. */
export const sections: NavItem[] = [
  { href: "/mods", label: "Моди" },
  { href: "/packs", label: "Збірки" },
  { href: "/skins", label: "Скіни" },
  { href: "/servers", label: "Сервери" },
  { href: "/help", label: "Допомога" },
];

/** Bottom bar on phones. */
export const tabBar: TabBarItem[] = [
  { href: "/", label: "Головна", icon: "home" },
  { href: "/search", label: "Пошук", icon: "search" },
  { href: "/share", label: "Поділитися", icon: "share" },
  { href: "/me", label: "Моє", icon: "user" },
];

export function isActive(pathname: string, href: string): boolean {
  return href === "/" ? pathname === "/" : pathname === href || pathname.startsWith(`${href}/`);
}
