FROM node:22-alpine AS builder
WORKDIR /src
COPY client/package.json client/package-lock.json* ./
RUN npm ci || npm install
COPY client/ ./
ARG NEXT_PUBLIC_API_BASE=http://localhost:8000
ENV NEXT_PUBLIC_API_BASE=$NEXT_PUBLIC_API_BASE
RUN npm run build
FROM node:22-alpine
WORKDIR /src
COPY --from=builder /src/package.json ./
COPY --from=builder /src/.next ./.next
COPY --from=builder /src/public ./public
COPY --from=builder /src/node_modules ./node_modules
COPY --from=builder /src/next.config.mjs ./next.config.mjs
EXPOSE 3000
CMD ["npm", "start"]
