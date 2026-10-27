# INT-05 paired captures

Two screens (`highlight`, `subtitles`), two viewports390x844/1440x900:

- `reference-*.png` / `reference-*.json`: original Stitch HTML + rendered button metrics, image requests successful.
- `baseline-*.png`: existing CMS5173 before this checkpoint, source missing in UI fixtures.
- `current-*.png`: final production Vite QA5174 bundle with range-capable existing8s video fixture.

Reference includes static data and cut elements; current uses isolated fixtures. Different video frames/content are not
pixel regressions. CMS exports have no separate mobile variant and keep desktop geometry when rendered at390.
These12 screenshots certify only the reviewed player checkpoint, not all screens or full design parity.
