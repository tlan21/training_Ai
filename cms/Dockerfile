# syntax=docker/dockerfile:1
FROM node:22-alpine AS builder
WORKDIR /src
COPY cms/package.json cms/package-lock.json* ./
RUN npm ci || npm install
COPY cms/ ./
ARG VITE_API_BASE=""
ENV VITE_API_BASE=$VITE_API_BASE
RUN npm run build

FROM nginx:alpine
COPY --from=builder /src/dist /usr/share/nginx/html
# SPA fallback: mọi route không phải file → index.html
RUN printf 'server { listen 80; root /usr/share/nginx/html; index index.html; location / { try_files $uri $uri/ /index.html; } location /api/ { proxy_pass http://gateway:8000; proxy_set_header Host $host; } }\n' > /etc/nginx/conf.d/default.conf
EXPOSE 80
