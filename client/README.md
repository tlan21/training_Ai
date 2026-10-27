# Client runtime

Browser API requests default to relative `/api`. Next forwards the existing gateway endpoints;
HttpOnly refresh cookies and Bearer headers use the same Client origin. API/refresh requests time out after10s.

- Host: `npm ci`, then `npm run build` and `npm start`. Internal gateway defaults to `http://127.0.0.1:8000`.
- Docker: Compose builds the rewrite with `http://gateway:8000`; no browser access to Docker DNS is required.
- Custom server gateway: set `GATEWAY_INTERNAL_URL` **before building**; rewrites are baked into Next's route manifest.
- Optional external browser API: set `NEXT_PUBLIC_API_BASE` before building. Leaving it empty keeps the same-origin proxy.

The proxy does not add gateway endpoints or change the public API contract. All authorization still belongs to the gateway.
If gateway forwarding fails, inspect its health and configured origin; do not change AI runtime/checkpoints.

Checks: `npx tsc --noEmit`, `npm run lint`, `npm run build` and the live session cases in `e2e/client_auth_live.spec.ts`.
Fresh Docker image builds remain subject to the shared disk-capacity gate; host build evidence does not prove a clean Docker build.

2026-10-27: fresh Client Docker build and isolated production proxy smoke PASS (see Codex verification/INT-16.md).
The smoke runs `e2e/client_container_smoke.cjs` inside the built image with networknone and `gateway=127.0.0.1`,
using an internal HTTP fixture; it checks the production page and cookie/Bearer/JSON/query/error forwarding without product services.
This is separate from the earlier live gateway browser tests.

Current public-deployment blocker: runtime audit flags the pinned Next14 as critical and its PostCSS dependency as high.
See Codex verification/INT-17.md for primary advisories and the proposed framework upgrade. No forced audit fix or major upgrade was applied.
