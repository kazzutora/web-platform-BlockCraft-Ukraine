# Development image: code is bind-mounted by docker-compose, node_modules live in a volume.
# The production (standalone) image arrives in stage 9.
FROM node:24-slim

ENV COREPACK_ENABLE_DOWNLOAD_PROMPT=0 \
    NEXT_TELEMETRY_DISABLED=1

RUN corepack enable

WORKDIR /app

# The store stays in the image, so `pnpm install` on container start is a no-op
# until pnpm-lock.yaml changes.
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile --store-dir /pnpm-store

COPY . .

EXPOSE 3000

CMD ["pnpm", "dev"]
