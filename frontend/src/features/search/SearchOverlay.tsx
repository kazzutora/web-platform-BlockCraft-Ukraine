"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { Dialog as DialogPrimitive } from "radix-ui";
import { type KeyboardEvent, useEffect, useId, useMemo, useState } from "react";

import { Icon } from "@/components/ui/Icon";
import { api } from "@/lib/api/client";
import { cn } from "@/lib/cn";
import { queryKeys } from "@/lib/query-keys";

import { searchCopy as copy } from "./copy";
import { HitContent } from "./HitContent";
import { hitHref } from "./hits";
import { useDebouncedValue } from "./useDebouncedValue";

/** Other parts of the page (the home hero) open the overlay with this event. */
export const OPEN_SEARCH_EVENT = "bc:open-search";

/** The header magnifier and Ctrl+K: suggestions while typing, arrows and Enter to go. */
export function SearchOverlay() {
  const router = useRouter();
  const listId = useId();
  const [open, setOpen] = useState(false);
  const [value, setValue] = useState("");
  // The highlighted row belongs to a query: a new query starts from the first row again
  const [cursor, setCursor] = useState({ q: "", index: 0 });
  const q = useDebouncedValue(value.trim(), 200);

  useEffect(() => {
    const onKey = (event: globalThis.KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setOpen(true);
      }
    };
    const onOpen = (event: Event) => {
      const initial = (event as CustomEvent<string | undefined>).detail;
      if (initial) setValue(initial);
      setOpen(true);
    };
    window.addEventListener("keydown", onKey);
    window.addEventListener(OPEN_SEARCH_EVENT, onOpen);
    return () => {
      window.removeEventListener("keydown", onKey);
      window.removeEventListener(OPEN_SEARCH_EVENT, onOpen);
    };
  }, []);

  const results = useQuery({
    queryKey: queryKeys.search.suggest(q),
    enabled: open && q.length >= 2,
    staleTime: 60_000,
    queryFn: async () => {
      const { data } = await api.GET("/api/v1/search", { params: { query: { q } } });
      if (!data) throw new Error("GET /api/v1/search failed");
      return data.groups;
    },
  });
  const groups = useMemo(() => results.data ?? [], [results.data]);
  const flat = useMemo(() => groups.flatMap((group) => group.results), [groups]);
  // Position of each group's first hit in `flat`: arrows move across groups
  const starts = useMemo(
    () =>
      groups.map((_, index) => groups.slice(0, index).reduce((n, g) => n + g.results.length, 0)),
    [groups],
  );
  const active = cursor.q === q ? cursor.index : 0;
  const setActive = (next: number) => setCursor({ q, index: next });

  function go(href: string) {
    setOpen(false);
    router.push(href);
  }

  function onKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "ArrowDown" && flat.length) {
      event.preventDefault();
      setActive((active + 1) % flat.length);
    } else if (event.key === "ArrowUp" && flat.length) {
      event.preventDefault();
      setActive((active - 1 + flat.length) % flat.length);
    } else if (event.key === "Enter" && value.trim()) {
      event.preventDefault();
      const hit = flat[active];
      go(
        hit && q === value.trim() ? hitHref(hit) : `/search?q=${encodeURIComponent(value.trim())}`,
      );
    }
  }

  const optionId = (index: number) => `${listId}-option-${index}`;
  return (
    <DialogPrimitive.Root
      open={open}
      onOpenChange={(next) => {
        setOpen(next);
        if (!next) setValue("");
      }}
    >
      <DialogPrimitive.Trigger asChild>
        <button
          type="button"
          aria-label={copy.open}
          className="inline-flex size-11 items-center justify-center hover:bg-line"
        >
          <Icon name="search" />
        </button>
      </DialogPrimitive.Trigger>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="fixed inset-0 z-40 bg-text/40 data-[state=open]:animate-fade-in" />
        <DialogPrimitive.Content
          aria-describedby={undefined}
          className="fixed inset-x-0 top-0 z-50 flex max-h-[85dvh] flex-col border-b border-line bg-bg text-text data-[state=open]:animate-fade-in md:top-20 md:left-1/2 md:w-full md:max-w-2xl md:-translate-x-1/2 md:border"
        >
          <DialogPrimitive.Title className="sr-only">{copy.title}</DialogPrimitive.Title>
          <div className="flex items-center gap-3 border-b border-line px-4">
            <Icon name="search" className="text-muted" />
            <input
              autoFocus
              type="text"
              role="combobox"
              aria-expanded={flat.length > 0}
              aria-controls={listId}
              aria-activedescendant={flat.length ? optionId(active) : undefined}
              aria-autocomplete="list"
              aria-label={copy.label}
              placeholder={copy.placeholder}
              value={value}
              onChange={(event) => setValue(event.target.value)}
              onKeyDown={onKeyDown}
              className="h-14 min-w-0 flex-1 bg-transparent text-base outline-none placeholder:text-muted"
            />
            <DialogPrimitive.Close
              aria-label={copy.close}
              className="inline-flex size-11 shrink-0 items-center justify-center hover:bg-line"
            >
              <Icon name="close" />
            </DialogPrimitive.Close>
          </div>

          <div className="overflow-y-auto p-2">
            {q.length < 2 ? (
              <p className="px-3 py-6 text-sm text-muted">{copy.hint}</p>
            ) : results.isError ? (
              <p className="px-3 py-6 text-sm text-muted">{copy.error}</p>
            ) : results.isPending ? (
              <p role="status" className="px-3 py-6 text-sm text-muted">
                {copy.loading}
              </p>
            ) : !flat.length ? (
              <p role="status" className="px-3 py-6 text-sm">
                {copy.empty(q)}
              </p>
            ) : (
              <div
                id={listId}
                role="listbox"
                aria-label={copy.title}
                className="flex flex-col gap-4"
              >
                {groups.map((group, groupIndex) => (
                  <div key={group.kind} role="group" aria-labelledby={`${listId}-${group.kind}`}>
                    <p id={`${listId}-${group.kind}`} className="caps px-3 pb-1 text-muted">
                      {copy.kinds[group.kind as keyof typeof copy.kinds]}
                    </p>
                    {group.results.map((hit, hitIndex) => {
                      const position = starts[groupIndex] + hitIndex;
                      return (
                        <div
                          key={`${hit.kind}-${hit.id}`}
                          id={optionId(position)}
                          role="option"
                          aria-selected={position === active}
                          onMouseEnter={() => setActive(position)}
                          onClick={() => go(hitHref(hit))}
                          className={cn(
                            "flex cursor-pointer items-center gap-4 px-3 py-2",
                            position === active &&
                              "bg-surface outline-2 -outline-offset-2 outline-accent",
                          )}
                        >
                          <HitContent hit={hit} />
                        </div>
                      );
                    })}
                  </div>
                ))}
              </div>
            )}
          </div>

          {value.trim() && (
            <button
              type="button"
              onClick={() => go(`/search?q=${encodeURIComponent(value.trim())}`)}
              className="flex h-12 items-center gap-2 border-t border-line px-5 text-sm hover:bg-surface"
            >
              <Icon name="search" size={16} />
              {copy.all(value.trim())}
            </button>
          )}
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}
