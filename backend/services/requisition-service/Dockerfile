# requisition-service image. Build context is backend/ (Readiness doc §2, Rule 2):
#   docker build -f services/requisition-service/Dockerfile backend/
# Coolify: Base Directory /backend, Dockerfile services/requisition-service/Dockerfile,
# watch paths backend/services/requisition-service/**, backend/packages/**, backend/package-lock.json

FROM node:20.20.2-alpine AS build
WORKDIR /app
COPY . .
RUN npm ci \
 && npm run build -w @teamora/platform \
 && npm run build -w @teamora/requisition-service

FROM node:20.20.2-alpine AS deps
WORKDIR /app
COPY . .
RUN npm ci --omit=dev

FROM node:20.20.2-alpine AS runtime
ENV NODE_ENV=production
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY --from=build /app/packages/platform/package.json ./packages/platform/package.json
COPY --from=build /app/packages/platform/dist ./packages/platform/dist
COPY --from=build /app/services/requisition-service/package.json ./services/requisition-service/package.json
COPY --from=build /app/services/requisition-service/dist ./services/requisition-service/dist
USER node
EXPOSE 3002
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD wget -qO- "http://127.0.0.1:${PORT:-3002}/health" > /dev/null || exit 1
CMD ["node", "services/requisition-service/dist/main.js"]
