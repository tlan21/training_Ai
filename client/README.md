# Client runtime

Client uses Next16.4.3 with React18.3.1; Node20.9+ is required (Docker uses Node22).
Production builds keep Webpack with `next build --webpack`; lint uses ESLint9 flat config through `eslint src`.
On a clean checkout, run `npx next typegen` before standalone `npx tsc --noEmit` so Next's generated route types exist.

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

2026-10-27 approved INT-17 upgrade: clean host/Docker installs, lint/types/build, Docker proxy smoke and53Client fixture E2E PASS.
Full and runtime-only npm audits report0findings. React18 remains supported but deprecated by Next16; React Compiler is not enabled.
Two newly added compiler-oriented lint diagnostics retain the previous React18 policy in eslint.config.mjs; existing hook/dependency checks remain.
The two live gateway session cases now pass on the deployed local Client image at localhost/127.0.0.1.
Local Compose deployment is verified; no master release or public-production readiness is implied by these checks.
See Codex verification/INT-17.md for migration details and the remaining live gate.
