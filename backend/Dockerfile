# syntax=docker/dockerfile:1
FROM golang:1.26-alpine AS builder
WORKDIR /src
COPY backend/go.mod backend/go.sum ./backend/
RUN --mount=type=cache,target=/go/pkg/mod cd backend && go mod download
COPY backend/ ./backend/
COPY infra/ ./infra/
RUN --mount=type=cache,target=/go/pkg/mod --mount=type=cache,target=/root/.cache/go-build \
    cd backend && CGO_ENABLED=0 GOOS=linux go build -o /out/gateway ./cmd/gateway && \
    CGO_ENABLED=0 GOOS=linux go build -o /out/orchestrator ./cmd/orchestrator && \
    CGO_ENABLED=0 GOOS=linux go build -o /out/ffmpeg-cutter ./cmd/ffmpeg-cutter && \
    CGO_ENABLED=0 GOOS=linux go build -o /out/ai-mock ./cmd/ai-mock

FROM alpine:3.20
RUN apk add --no-cache ca-certificates ffmpeg
WORKDIR /srv
COPY --from=builder /out/gateway /out/orchestrator /out/ffmpeg-cutter /usr/local/bin/
COPY --from=builder /out/ai-mock /usr/local/bin/
# backend cần openapi gen runtime (đã embed), không cần infra khi chạy
EXPOSE 8000
