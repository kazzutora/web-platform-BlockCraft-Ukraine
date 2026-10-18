import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  cacheComponents: true,
  // No X-Powered-By: Nginx sends the security headers for every response
  poweredByHeader: false,
  images: {
    // Icons and gallery of mods, packs and shaders live on Modrinth's CDN
    remotePatterns: [{ protocol: "https", hostname: "cdn.modrinth.com" }],
  },
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
