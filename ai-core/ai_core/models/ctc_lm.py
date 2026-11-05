"""AI-26: CTC prefix beam search with a syllable lexicon + own bigram LM (shallow fusion at syllable boundaries).

The acoustic model is unchanged; the LM only re-ranks CTC prefixes. Text is the ASR label space: upper-case NFC syllables
separated by spaces. Score = log P_ctc + alpha * log P_lm(syllables) + beta * #syllables; out-of-lexicon syllables pay `oov`.
"""
import json
import math
import re
import unicodedata
from collections import Counter, defaultdict

_NEG_INF = float("-inf")
BOS = "<s>"


def _lse(a: float, b: float) -> float:
    if a == _NEG_INF:
        return b
    if b == _NEG_INF:
        return a
    m = max(a, b)
    return m + math.log1p(math.exp(-abs(a - b)))


def syllables(text: str) -> list[list[str]]:
    """Sentences of upper-case syllables; punctuation splits sentences or is dropped."""
    text = unicodedata.normalize("NFC", text).upper()
    out = []
    for sentence in re.split(r"[.!?;:\n]+", text):
        words = [w for w in re.split(r"[^\w]+", sentence) if w and not w.isdigit()]
        if words:
            out.append(words)
    return out


class SyllableLM:
    """Interpolated absolute-discount bigram over syllables (Kneser-Ney style backoff weight, add-one unigram)."""

    def __init__(self, unigram: dict, bigram: dict, d: float = 0.75):
        self.unigram, self.bigram, self.d = unigram, bigram, d
        self.total = sum(unigram.values())
        self.vocab = len(unigram) + 1
        self.context = {v: (sum(f.values()), len(f)) for v, f in bigram.items()}
        self.prefixes = {w[:i] for w in unigram for i in range(1, len(w) + 1)}

    @classmethod
    def train(cls, sentences, min_unigram: int = 2, min_bigram: int = 2, d: float = 0.75):
        uni, bi = Counter(), defaultdict(Counter)
        for words in sentences:
            uni.update(words)
            for v, w in zip([BOS] + words, words):
                bi[v][w] += 1
        keep = {w: c for w, c in uni.items() if c >= min_unigram}
        bigram = {v: {w: c for w, c in f.items() if c >= min_bigram and w in keep} for v, f in bi.items() if v in keep or v == BOS}
        return cls(keep, {v: f for v, f in bigram.items() if f}, d)

    def save(self, path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"d": self.d, "unigram": self.unigram, "bigram": self.bigram}, f, ensure_ascii=False, separators=(",", ":"))

    @classmethod
    def load(cls, path):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return cls(data["unigram"], data["bigram"], data["d"])

    def known(self, word: str) -> bool:
        return word in self.unigram

    def is_prefix(self, part: str) -> bool:
        return part in self.prefixes

    def logp(self, word: str, prev: str) -> float:
        uni = (self.unigram.get(word, 0) + 1) / (self.total + self.vocab)
        seen = self.context.get(prev)
        if not seen:
            return math.log(uni)
        count, followers = seen
        c = self.bigram[prev].get(word, 0)
        return math.log(max(c - self.d, 0) / count + self.d * followers / count * uni)


def ctc_lm_decode(rows, vocab, lm: SyllableLM, alpha: float = 0.5, beta: float = 1.0, beam: int = 16,
                  oov: float = -10.0, prune: float = -12.0, blank: int = 0, partial: float | None = None) -> tuple[str, float]:
    """rows: per-frame log-probs (lists of floats), vocab[i] = symbol of class i (vocab[0] = blank).

    Returns (text, best path's CTC log-prob per frame) — the latter is a confidence signal independent of the lexicon."""
    space = vocab.index(" ")
    partial = oov / 4 if partial is None else partial  # per char of a syllable prefix unknown to the lexicon

    def lm_word(prefix: str) -> float:
        """LM score of the syllable that ends `prefix` (committed text, last char not a space)."""
        words = prefix.split()
        word, prev = words[-1], words[-2] if len(words) > 1 else BOS
        if not lm.known(word):
            return oov + beta
        return alpha * lm.logp(word, prev if lm.known(prev) else BOS) + beta

    # prefix -> (p_blank, p_nonblank, lm_score, last_class); lm_score depends only on the prefix text
    beams = {"": (0.0, _NEG_INF, 0.0, None)}
    for row in rows:
        cand = [c for c in range(1, len(row)) if row[c] > prune] or [max(range(1, len(row)), key=row.__getitem__)]
        nxt: dict[str, list] = {}

        def add(prefix, pb, pnb, lm_score, last):
            cur = nxt.get(prefix)
            if cur is None:
                nxt[prefix] = [pb, pnb, lm_score, last]
            else:
                cur[0], cur[1] = _lse(cur[0], pb), _lse(cur[1], pnb)

        for prefix, (pb, pnb, lm_score, last) in beams.items():
            total = _lse(pb, pnb)
            add(prefix, total + row[blank], _NEG_INF, lm_score, last)
            for c in cand:
                p = row[c]
                if c == last:
                    add(prefix, _NEG_INF, pnb + p, lm_score, last)       # repeated class collapses
                    source = pb                                          # same symbol again only after a blank
                else:
                    source = total
                if source == _NEG_INF:
                    continue
                if c == space:
                    if not prefix or prefix.endswith(" "):
                        add(prefix, _NEG_INF, source + p, lm_score, last)  # leading/double space is a no-op
                    else:
                        add(prefix + " ", _NEG_INF, source + p, lm_score + lm_word(prefix), c)
                    continue
                ext = prefix + vocab[c]
                penalty = 0.0 if lm.is_prefix(ext.rsplit(" ", 1)[-1]) else partial  # soft lexicon constraint inside a syllable
                add(ext, _NEG_INF, source + p, lm_score + penalty, c)
        beams = dict(sorted(((k, tuple(v)) for k, v in nxt.items()),
                            key=lambda kv: _lse(kv[1][0], kv[1][1]) + kv[1][2], reverse=True)[:beam])

    def final(item):
        prefix, (pb, pnb, lm_score, _) = item
        tail = lm_word(prefix) if prefix and not prefix.endswith(" ") else 0.0
        return _lse(pb, pnb) + lm_score + tail

    best = max(beams.items(), key=final)
    return best[0].strip(), _lse(best[1][0], best[1][1]) / max(len(rows), 1)
