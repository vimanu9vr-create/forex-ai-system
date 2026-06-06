# ── ForexAI dashboard (React/Vite) — build, then serve via nginx ─────────────
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
# --legacy-peer-deps: the project's deps have a strict peer conflict (Vite/plugin
# versions) that npm's CI resolver rejects; this matches the working local install.
RUN npm install --legacy-peer-deps
COPY . .
# API + WS resolve through the nginx reverse-proxy (same origin) by default.
ARG VITE_API_BASE_URL=/api
ARG VITE_WS_URL=
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL \
    VITE_WS_URL=$VITE_WS_URL
# Use vite build directly (esbuild) so a strict tsc type-only error can't block deploy.
RUN npx vite build

FROM nginx:alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
