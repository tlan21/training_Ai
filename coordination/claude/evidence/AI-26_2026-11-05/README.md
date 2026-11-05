# AI-26 — lexicon + own bigram LM for CTC decoding: no meaningful gain at current acoustic quality (test NOT scored)

LM: own syllable bigram (absolute discount), 17.9M syllables (4,539 football-keyword + general Binhvq train articles, VIVOS train transcripts),
36,884 syllables / 733,510 bigrams, 8 MB (`lm_manifest.json`). Decoder: `ai_core/models/ctc_lm.py` (prefix beam 16, shallow fusion at
syllable boundaries, soft lexicon prefix penalty), tests `ai_core/tests/test_ctc_lm.py`.

Dev only (14 football train + 10 frozen news val clips; tuning never touched the test sets) — `lm_dev_partial.log`:
- greedy CER 69.40% / WER 105.1%; best of 42+ settings (alpha 0.2, beta 2, partial −1, oov −5): CER 66.92% / WER 116.0%.
- Side check on 12 AI-02 reviewed news clips (not dev/test): greedy CER 64.4% → best 59.4% (alpha 0.1, beta 2), WER worse or flat.
- An earlier run was stopped before its test stage when the dev optimum sat on the grid edge; no test result was produced or viewed.

Decision: pre-registered test (football 30 / VIVOS test) not run — dev shows ≤2.5 pt CER and higher WER, below any deployable benefit.
Cause: the acoustic model gets ~2/3 of characters wrong on real audio, so the right syllables are rarely among the CTC candidates; a lexicon/LM
re-ranks but cannot recover them. Revisit once acoustic CER on real audio is much lower (LM fusion typically helps when CER is ~10–30%).
