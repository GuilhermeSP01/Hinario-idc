# syntax=docker/dockerfile:1
FROM node:24-bookworm-slim AS dependencies
WORKDIR /app
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml tsconfig.base.json ./
COPY apps/mobile/package.json apps/mobile/package.json
COPY packages/core/package.json packages/core/package.json
COPY packages/observability/package.json packages/observability/package.json
COPY packages/firebase/package.json packages/firebase/package.json
COPY packages/hymns-contracts/package.json packages/hymns-contracts/package.json
# Optional CA for HTTPS-inspecting development environments; never stored in a layer.
RUN --mount=type=cache,id=hinario-npm,target=/root/.npm \
    --mount=type=secret,id=proxy_ca \
    if [ -f /run/secrets/proxy_ca ]; then export NODE_EXTRA_CA_CERTS=/run/secrets/proxy_ca; fi; \
    NODE_USE_ENV_PROXY=1 corepack pnpm install --frozen-lockfile --filter @hinario/mobile...
COPY packages/core packages/core
COPY packages/observability packages/observability
COPY packages/firebase packages/firebase
COPY packages/hymns-contracts packages/hymns-contracts
COPY apps/mobile apps/mobile

FROM dependencies AS development
EXPOSE 5173
CMD ["corepack", "pnpm", "--filter", "@hinario/mobile", "dev", "--host", "0.0.0.0", "--port", "5173", "--strictPort"]

FROM dependencies AS build
# Vite embeds these public Firebase settings at build time (not runtime).
ARG VITE_LOG_LEVEL=info
ARG VITE_FIREBASE_API_KEY
ARG VITE_FIREBASE_AUTH_DOMAIN
ARG VITE_FIREBASE_PROJECT_ID
ARG VITE_FIREBASE_STORAGE_BUCKET
ARG VITE_FIREBASE_MESSAGING_SENDER_ID
ARG VITE_FIREBASE_APP_ID
RUN corepack pnpm --filter @hinario/mobile build \
    && chmod -R a+rX apps/mobile/dist

FROM nginxinc/nginx-unprivileged:stable-alpine AS production
COPY --chmod=644 apps/mobile/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/apps/mobile/dist /usr/share/nginx/html
EXPOSE 8080
