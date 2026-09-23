# auth-service image. Build context is backend/ (Readiness doc §2, Rule 2):
#   docker build -f services/auth-service/Dockerfile backend/
# Coolify: Base Directory /backend, Dockerfile services/auth-service/Dockerfile,
# watch paths backend/services/auth-service/**, backend/packages/**, backend/package-lock.json

FROM node:24.21.0-alpine AS build
WORKDIR /app
COPY . .
RUN npm ci \
 && npm run build -w @teamora/platform \
 && npm run build -w @teamora/auth-service

FROM node:24.21.0-alpine AS deps
WORKDIR /app
COPY . .
RUN npm ci --omit=dev

FROM node:24.21.0-alpine AS runtime
ENV NODE_ENV=production
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY --from=build /app/packages/platform/package.json ./packages/platform/package.json
COPY --from=build /app/packages/platform/dist ./packages/platform/dist
COPY --from=build /app/services/auth-service/package.json ./services/auth-service/package.json
COPY --from=build /app/services/auth-service/dist ./services/auth-service/dist
USER node
EXPOSE 3001
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD wget -qO- "http://127.0.0.1:${PORT:-3001}/health" > /dev/null || exit 1
CMD ["node", "services/auth-service/dist/main.js"]
