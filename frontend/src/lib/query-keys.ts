/** TanStack Query keys, one object per domain. */
export const queryKeys = {
  me: {
    all: ["me"] as const,
    account: () => [...queryKeys.me.all, "account"] as const,
    settings: () => [...queryKeys.me.all, "settings"] as const,
  },
  auth: {
    config: ["auth", "config"] as const,
  },
  library: {
    all: ["library"] as const,
    saved: (kind: string, gameVersion = "") =>
      [...queryKeys.library.all, "saved", kind, gameVersion] as const,
    myCollections: (kind = "", id = "") =>
      [...queryKeys.library.all, "my-collections", kind, id] as const,
    collection: (id: number) => [...queryKeys.library.all, "collection", id] as const,
  },
  skins: {
    all: ["skins"] as const,
    catalog: (query: object) => [...queryKeys.skins.all, "catalog", query] as const,
    mine: () => [...queryKeys.skins.all, "mine"] as const,
    lookup: (nickname: string) =>
      [...queryKeys.skins.all, "lookup", nickname.toLowerCase()] as const,
  },
  search: {
    suggest: (q: string) => ["search", "suggest", q] as const,
  },
  servers: {
    all: ["servers"] as const,
    catalog: (query: object) => [...queryKeys.servers.all, "catalog", query] as const,
    stats: (slug: string, range: string) =>
      [...queryKeys.servers.all, "stats", slug, range] as const,
    verification: (slug: string) => [...queryKeys.servers.all, "verification", slug] as const,
    mine: () => [...queryKeys.servers.all, "mine"] as const,
  },
  social: {
    reviews: (kind: string, id: string, sort: string) =>
      ["social", "reviews", kind, id, sort] as const,
    reviewsOf: (kind: string, id: string) => ["social", "reviews", kind, id] as const,
    comments: (kind: string, id: string) => ["social", "comments", kind, id] as const,
  },
};
