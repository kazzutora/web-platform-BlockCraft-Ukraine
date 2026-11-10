import { packsCopy } from "./copy";
import type { PackItem } from "./types";

const reasons = packsCopy.detail.reason;
const order = { requested: 0, implicit: 1, dependency: 2 } as const;

/** The author's picks first, then shader engines, then libraries. */
export function sortItems(items: PackItem[]): PackItem[] {
  return [...items].sort((a, b) => order[a.reason] - order[b.reason]);
}

/** «потрібен для Sodium Extra» — empty for what the author picked. */
export function reasonOf(item: PackItem, titles: Map<string, string>): string {
  const by = item.required_by.map((slug) => titles.get(slug) ?? slug).join(", ");
  if (item.reason === "dependency") return reasons.dependency(by);
  if (item.reason === "implicit") return reasons.implicit(by);
  return "";
}
