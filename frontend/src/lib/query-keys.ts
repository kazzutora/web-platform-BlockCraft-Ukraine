/** TanStack Query keys, one object per domain. */
export const queryKeys = {
  meta: ["meta"] as const,
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
    addJob: (id: string) => [...queryKeys.skins.all, "add-job", id] as const,
  },
  notifications: {
    all: ["notifications"] as const,
    unread: () => [...queryKeys.notifications.all, "unread"] as const,
    list: () => [...queryKeys.notifications.all, "list"] as const,
  },
  compat: {
    install: (slug: string, gameVersion: string, loader: string) =>
      ["compat", "install", slug, gameVersion, loader] as const,
  },
  imports: {
    check: (target: object | null, versions: string[]) =>
      ["imports", "check", target, versions] as const,
    updates: (target: object | null, hashes: string[]) =>
      ["imports", "updates", target, hashes] as const,
  },
  mods: {
    importJob: (id: string) => ["mods", "import-job", id] as const,
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
  packs: {
    all: ["packs"] as const,
    catalog: (query: object) => [...queryKeys.packs.all, "catalog", query] as const,
    detail: (slug: string) => [...queryKeys.packs.all, "detail", slug] as const,
    mine: () => [...queryKeys.packs.all, "mine"] as const,
    search: (query: object) => [...queryKeys.packs.all, "search", query] as const,
    /** Mutation key of «add a mod», to show the rows still being saved. */
    adding: (slug: string) => [...queryKeys.packs.all, "adding", slug] as const,
    retarget: (slug: string, gameVersion: string, loader: string) =>
      [...queryKeys.packs.all, "retarget", slug, gameVersion, loader] as const,
  },
  social: {
    reviews: (kind: string, id: string, sort: string) =>
      ["social", "reviews", kind, id, sort] as const,
    reviewsOf: (kind: string, id: string) => ["social", "reviews", kind, id] as const,
  },
};
