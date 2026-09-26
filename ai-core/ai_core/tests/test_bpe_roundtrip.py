"""BPE encode→decode khôi phục nguyên văn 100% trên 10.000 câu — evaluation_plan §2.3."""

import random

from ai_core.tokenizer import BPETokenizer

_WORDS = ["xin", "chào", "việt", "nam", "highlight", "bóng", "đá", "trận", "đấu",
          "the", "quick", "brown", "fox", "1234", "a", "AI", "phân", "tích", "video"]


def _make_sentences(n: int, seed: int = 0) -> list[str]:
    rng = random.Random(seed)
    out = []
    for _ in range(n):
        k = rng.randint(1, 12)
        out.append(" ".join(rng.choice(_WORDS) for _ in range(k)))
    return out


def test_roundtrip_10000_sentences():
    train_corpus = _make_sentences(2000, seed=1)
    tok = BPETokenizer(vocab_size=1024)
    tok.train(train_corpus, min_freq=1)

    for s in _make_sentences(10000, seed=2):
        assert tok.decode(tok.encode(s)) == s


def test_vocab_size_target():
    corpus = _make_sentences(3000, seed=3)
    tok = BPETokenizer(vocab_size=600)
    tok.train(corpus, min_freq=1)
    assert tok.vocab_size <= 600


def test_save_load_roundtrip(tmp_path):
    tok = BPETokenizer(vocab_size=512)
    tok.train(_make_sentences(1000, seed=4), min_freq=1)
    path = str(tmp_path / "vocab.json")
    tok.save(path)
    tok2 = BPETokenizer.load(path)
    s = "xin chào việt nam highlight"
    assert tok2.encode(s) == tok.encode(s)
    assert tok2.decode(tok2.encode(s)) == s


def test_space_attaches_to_following_word():
    """Dấu cách phải dính vào từ sau (" phố"), không đứng riêng. Bản cũ tách riêng từng dấu cách nên
    tiếng Việt tốn gấp đôi token — câu 20 từ ra 41 token, context 1024 chỉ chứa ~500 từ."""
    from ai_core.tokenizer.bpe import _CHUNK_RE

    assert _CHUNK_RE.findall("Thành phố Hồ Chí Minh") == ["Thành", " phố", " Hồ", " Chí", " Minh"]
    for s in ["a  b", "x\n Hà\n\nY", "  đầu", "cuối  ", "\t"]:
        assert "".join(_CHUNK_RE.findall(s)) == s                  # không mất ký tự nào
