# --- build stage ---
FROM node:22-alpine AS builder
WORKDIR /app
ARG NEXT_PUBLIC_READ_ONLY=false
ENV NEXT_PUBLIC_READ_ONLY=$NEXT_PUBLIC_READ_ONLY
ENV NEXT_TELEMETRY_DISABLED=1
COPY package.json package-lock.json* ./
RUN npm ci
COPY . .
RUN npm run build

# --- runtime stage (Next.js standalone output) ---
FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV HOSTNAME=0.0.0.0
ENV PORT=3000

COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

EXPOSE 3000
CMD ["node", "server.js"]
