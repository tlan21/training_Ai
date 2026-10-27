# INT-17 — Client framework security decision (2026-10-27)

Owner CODEX. Status BLOCKED: major framework upgrade decision required under user's significant-architecture-change rule.
This is a confirmed dependency finding from INT-16 fresh Docker npm ci, not a hypothetical warning or proof of exploitation.
No package/source migration, forced install, audit fix, public deployment or AI change performed.

## Evidence
- Fresh Client image builds with pinned Next14.2.35; npm ci reports6 vulnerable packages overall.
- Readonly `cd client; npm audit --omit=dev --json`: Nextcritical +PostCSShigh (2runtime packages), raw INT-16-runtime-audit.json.
  npm proposes next16.4.3 with isSemVerMajor=true. Registry `npm view next@14 version --json` ends at14.2.35;
  latest15=15.5.28. Node22 image satisfies the reported Node>=20.9 requirement for16.4.3.
- Primary maintainer advisories checked2026-10-27:
  - [GHSA-p293-qw3h-jr36](https://github.com/vercel/next.js/security/advisories/GHSA-p293-qw3h-jr36): unauthenticated RCE
    on Windows filesystems, affected13.4..<15.5.24 and16..<16.3.3; no known Windows workaround; fixes15.5.24/16.3.3.
    Previous host Client ran on Windows; currently stopped. Linux image does not establish exposure to this Windows-specific path.
  - [GHSA-ggv3-7p47-pfv8](https://github.com/vercel/next.js/security/advisories/GHSA-ggv3-7p47-pfv8): request smuggling
    via chunked DELETE/OPTIONS in self-hosted external rewrites; fixes15.5.13/16.1.7. This Client uses external gateway rewrites;
    gateway still enforces JWT/roles. Passing ordinary proxy requests is not an adversarial security verification.
  - [GHSA-2xp9-vwfh-vxw4](https://github.com/vercel/next.js/security/advisories/GHSA-2xp9-vwfh-vxw4): Image Optimization AVIF RCE,
    fixes15.5.24/16.3.3. Client uses existing img thumbnails; no exploit or optimizer-route exposure is asserted here.
  The raw audit includes additional advisories; resolving these examples alone is not a clean audit.

## Concrete proposed scope for approval
- Upgrade Client Next to16.4.3 (registry audit proposal) and compatible eslint-config-next; update the lockfile through npm.
  Keep React18 if supported/verified; request further scope only if framework compatibility makes a React major necessary.
- Adjust existing build/lint/config and route parameter handling only where required by migration. Preserve public OpenAPI0.3.1,
  same-origin gateway proxy/cookie/JWT semantics, existing Stitch screens and deferred forgot-password behavior.
- Verify clean npm ci, tsc/lint/build, Docker build, production proxy smoke, full55Client E2E +live gateway sessions after runtime recovery.
  Rerun runtime audit; document any remaining finding rather than suppressing it. No production release without its normal approval gates.
- Expected files: client/package*.json, config/type definitions and existing route callers if compatibility requires;
  existing E2E fixtures/config only as needed, Codex evidence/tracker. No API/DB/Claude edits or new business capability.

Acceptance: approved scoped migration, required checks PASS, critical/high runtime findings resolved or explicitly reviewed,
UI/API behavior preserved. Current build is functionally verified for isolated development; public deployment remains gated.
