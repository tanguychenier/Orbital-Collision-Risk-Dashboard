# ----------------------------------------------------------------------------
# Multi-stage build: pnpm install + build, then nginx serves the static SPA.
# ----------------------------------------------------------------------------
FROM node:25-alpine AS builder
ENV PNPM_HOME=/pnpm \
    PATH=/pnpm:$PATH \
    CI=true
RUN corepack enable

WORKDIR /app

# Install dependencies first to leverage Docker layer caching
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

# Build args read by Vite at build time
ARG VITE_API_BASE_URL=http://localhost:8000/api
ARG VITE_USE_MSW=false
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL \
    VITE_USE_MSW=$VITE_USE_MSW

COPY . .
RUN pnpm typecheck && pnpm build

# ----------------------------------------------------------------------------
FROM nginx:1.27-alpine AS runtime
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD wget -qO- http://localhost/ >/dev/null 2>&1 || exit 1
CMD ["nginx", "-g", "daemon off;"]
