# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# ============================================
# Stage 1: Build the static documentation portal (all locales)
# ============================================
FROM node:20-slim AS builder

ARG DOCS_APP_URL=http://localhost:8001
ENV DOCS_APP_URL=${DOCS_APP_URL}

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

# ============================================
# Stage 2: Serve the static site (non-root nginx)
# ============================================
FROM nginxinc/nginx-unprivileged:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/build /usr/share/nginx/html

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -q --spider http://127.0.0.1:8080/ || exit 1
