import type { NextConfig } from "next";

// File change events do not reach Docker containers from Windows drives,
// so docker-compose enables polling. Locally the native watcher is used.
const pollIntervalMs = Number(process.env.WATCH_POLL_INTERVAL_MS) || undefined;

const nextConfig: NextConfig = {
  ...(pollIntervalMs && { watchOptions: { pollIntervalMs } }),
  cacheComponents: true,
  partialPrefetching: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
