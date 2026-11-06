# Dependency vulnerability check (user 2026-11-06 "hãy kiểm tra phiên bản có bị dính ver chứa lỗ hổng bảo mật không")

Tools: govulncheck (latest, reachability-aware), npm audit (lockfiles), pip-audit 2.10.1 (OSV/PyPI). Commit scanned: f496ff2 (= master).

| Area | Runtime? | Result | Fix |
|---|---|---|---|
| Go stdlib | gateway binary built with **go1.26.10** | 32 reachable stdlib advisories reported against `go 1.26.0` in go.mod — all fixed by ≤ go1.26.10, i.e. **not present in the running binary** | add `toolchain go1.26.10` floor so local/CI builds can't use an older toolchain |
| github.com/getkin/kin-openapi v0.145.0 | yes (gateway) | GO-2026-6795 YAML NaN/Inf panic via OAS (reachable) | ≥ v0.148.0 |
| github.com/klauspost/compress v1.19.2 | yes | GO-2026-6865 panic on two-block frames (reachable) | ≥ v1.20.2 |
| github.com/quic-go/quic-go v0.59.0 | yes | GO-2026-5676 HTTP/3 QPACK trailer memory exhaustion (reachable) | ≥ v0.59.1 |
| gateway base image `alpine:3.20` | yes | Alpine 3.20 is past end of support (ended 2026-04) — no OS security fixes | `alpine:3.24` (CMS/Client already on 3.24) |
| CMS (prod deps) | yes | follow-redirects 1.16.0–1.16.1 **high** (credentials/sensitive headers on redirect); react-router(-dom) ≤ 7.17.0 moderate (open redirect via backslash in `<Link>`/`useNavigate`; SSR item not applicable — CMS is SPA) | follow-redirects patch (npm audit fix); react-router ≥ 7.18.5 (major 6→7 upgrade) |
| CMS (dev only) | no | vite (high, dev-server path traversal), esbuild (moderate, dev server) | upgrade when convenient; not shipped |
| Client (prod deps) | yes | **0** | — |
| Client (dev only) | no | 8 moderate (typescript-eslint → minimatch ReDoS) | upgrade eslint toolchain |
| inference-service container (36 pinned pkgs, pip freeze) | yes | **0** known (torch 2.15.0 audited separately: 0) | — |
| ai-core local training venv | no (dev/Kaggle only) | pillow 12.3.0 (39, fix 13.0.0), filelock 3.32.2 (12, fix 4.2.1), certifi 2026.7.22 (2), werkzeug 3.1.8 (1, via tensorboard) | pip upgrade in the venv |
| Container OS packages | — | not scanned: `docker scout` needs `docker login` (user action) | — |
