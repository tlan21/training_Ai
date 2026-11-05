import math

from ai_core.models.ctc_lm import SyllableLM, ctc_lm_decode, syllables

VOCAB = ["<blank>", " ", "B", "A", "N", "O"]


def frames(*dists):
    """Each dist: {symbol: prob}; the rest is spread over the other classes."""
    rows = []
    for d in dists:
        rest = (1 - sum(d.values())) / (len(VOCAB) - len(d))
        rows.append([math.log(d.get(s, rest)) for s in VOCAB])
    return rows


def test_lm_probabilities_and_syllable_split():
    assert syllables("Bàn thắng, phút 90! Hay quá") == [["BÀN", "THẮNG", "PHÚT"], ["HAY", "QUÁ"]]
    lm = SyllableLM.train([["BAN", "BAO"]] * 3 + [["BAO", "BAN"]] * 2, min_unigram=1, min_bigram=1)
    mass = sum(math.exp(lm.logp(w, "BAN")) for w in lm.unigram)  # the small remainder is reserved for unseen syllables
    assert 0.95 < mass <= 1.0
    assert lm.logp("BAO", "BAN") > lm.logp("BAN", "BAN")


def test_lexicon_breaks_an_acoustic_tie():
    lm = SyllableLM.train([["BAN"]] * 5, min_unigram=1, min_bigram=1)
    # third symbol is ambiguous N vs O; greedy picks O ("BAO", not a word), the lexicon picks "BAN"
    rows = frames({"B": .9}, {"A": .9}, {"O": .46, "N": .44}, {"<blank>": .9})
    assert ctc_lm_decode(rows, VOCAB, lm, alpha=0.0, beta=0.0, oov=0.0)[0] == "BAO"   # no LM = greedy-like
    text, confidence = ctc_lm_decode(rows, VOCAB, lm, alpha=0.5, beta=0.0, oov=-10.0)
    assert text == "BAN" and confidence < 0
