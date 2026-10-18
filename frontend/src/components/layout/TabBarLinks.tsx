import Link from "next/link";

import { Icon } from "@/components/ui/Icon";
import { cn } from "@/lib/cn";

import { isActive, tabBar } from "./navigation";

const copy = { label: "Швидкі дії" };

/** Bottom bar on phones: Головна · Пошук · Додати · Обране. */
export function TabBarLinks({ pathname = null }: { pathname?: string | null }) {
  return (
    <nav
      aria-label={copy.label}
      className="fixed inset-x-0 bottom-0 z-30 border-t border-line bg-bg pb-[env(safe-area-inset-bottom)] md:hidden"
    >
      <ul className="grid grid-cols-4">
        {tabBar.map((item) => {
          const active = pathname !== null && isActive(pathname, item.href);
          return (
            <li key={item.href}>
              <Link
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "flex h-16 flex-col items-center justify-center gap-1 text-[0.6875rem] font-medium",
                  active ? "text-text" : "text-muted",
                )}
              >
                <Icon name={item.icon} />
                {item.label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
