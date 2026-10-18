# Two targets: `dev` (pnpm dev, code bind-mounted by docker-compose.yml)
# and `prod` (next build in standalone mode, only the server and its files).
FROM node:24-slim AS base

ENV COREPACK_ENABLE_DOWNLOAD_PROMPT=0 \
    NEXT_TELEMETRY_DISABLED=1

RUN corepack enable

WORKDIR /app


FROM base AS dev

# The store stays in the image, so `pnpm install` on container start is a no-op
# until pnpm-lock.yaml changes.
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile --store-dir /pnpm-store

COPY . .

EXPOSE 3000

CMD ["pnpm", "dev"]


FROM base AS build

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN --mount=type=cache,target=/pnpm-store pnpm install --frozen-lockfile --store-dir /pnpm-store

COPY . .

# Public variables are baked into the bundle at build time
ARG NEXT_PUBLIC_SITE_URL
ENV NEXT_PUBLIC_SITE_URL=$NEXT_PUBLIC_SITE_URL
RUN pnpm build


FROM node:24-slim AS prod

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    HOSTNAME=0.0.0.0 \
    PORT=3000

WORKDIR /app

COPY --from=build --chown=node:node /app/.next/standalone ./
COPY --from=build --chown=node:node /app/.next/static ./.next/static
COPY --from=build --chown=node:node /app/public ./public

USER node

EXPOSE 3000

CMD ["node", "server.js"]
