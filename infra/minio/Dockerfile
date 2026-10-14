FROM golang:1.22-alpine AS builder
RUN apk add --no-cache ca-certificates
WORKDIR /src
# Build the same official release when its old registry image is unavailable.
RUN wget -q https://github.com/minio/minio/archive/refs/tags/RELEASE.2024-06-13T22-53-53Z.tar.gz -O /tmp/source.tar.gz \
    && tar -xzf /tmp/source.tar.gz --strip-components=1
RUN --mount=type=cache,target=/go/pkg/mod CGO_ENABLED=0 go build -o /out/minio .

FROM alpine:3.20
RUN apk add --no-cache ca-certificates curl
COPY --from=builder /out/minio /usr/local/bin/minio
COPY --from=builder /src/LICENSE /licenses/minio/LICENSE
ENTRYPOINT ["minio"]
