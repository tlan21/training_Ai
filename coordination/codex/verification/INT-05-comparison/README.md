# INT-05 paired captures

Eight screens (`dashboard`, `queue`, `videos`, `highlight`, `subtitles`, `categories`, `published`, `settings`), two viewports390x844/1440x900:

- `reference-*.png` / `reference-*.json`: original Stitch HTML + rendered button metrics, image requests successful.
- `baseline-*.png`: existing CMS5173 before this checkpoint, source missing in UI fixtures.
- `current-*.png`: final production Vite QA5174 bundle for highlight/subtitles with range-capable existing8s video fixture.
  Other page sources are unchanged; their baseline captures remain labelled baseline, not newly deployed screenshots.

Reference includes static data and cut elements; current uses isolated fixtures. Different video frames/content are not
pixel regressions. CMS exports have no separate mobile variant and keep desktop geometry when rendered at390.
The36 screenshots document reference/baseline comparisons and the reviewed player checkpoint, not full design parity.
