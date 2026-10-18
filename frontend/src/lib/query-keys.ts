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
};
