"""T1.6b — dữ liệu pretrain: tách val theo BÀI, BPE không thấy val, token đọc lại đúng."""

import json
import math

import torch

from ai_core.tokenizer import BPETokenizer
from ai_core.training.datasets import TokenFileDataset


def _jsonl(tmp_path, texts):
    d = tmp_path / "wiki_json" / "AA"
    d.mkdir(parents=True)
    with open(d / "wiki_00", "w", encoding="utf-8") as f:
        for i, t in enumerate(texts):
            f.write(json.dumps({"id": str(i), "title": f"t{i}", "text": t}, ensure_ascii=False) + "\n")
    return str(tmp_path / "wiki_json" / "*" / "wiki_*")


def _run(monkeypatch, *argv):
    from ai_core.scripts import tokenize_corpus
    monkeypatch.setattr("sys.argv", ["tokenize_corpus", *argv])
    tokenize_corpus.main()


def test_val_split_by_document_and_bpe_sample_excludes_val(tmp_path, monkeypatch):
    docs = [f"Bài số {i}: Hà Nội là thủ đô của Việt Nam, dân số đông." * 3 for i in range(40)]
    glob_ = _jsonl(tmp_path, docs + ["ngắn"])                    # bài ngắn phải bị bỏ
    sample = tmp_path / "sample.txt"
    _run(monkeypatch, "--jsonl", glob_, "--min-chars", "50", "--val-every", "10",
         "--bpe-sample", str(sample), "--bpe-sample-every", "1")
    lines = sample.read_text(encoding="utf-8").splitlines()
    val_docs = {docs[i] for i in range(0, 40, 10)}
    assert len(lines) == 36 and not (set(lines) & val_docs)     # 40 − 4 bài val, không có bài val

    tok = BPETokenizer(vocab_size=320)
    tok.train(lines, min_freq=2)
    vocab = tmp_path / "bpe.json"
    tok.save(str(vocab))
    out = tmp_path / "tokens"
    _run(monkeypatch, "--jsonl", glob_, "--min-chars", "50", "--val-every", "10",
         "--vocab", str(vocab), "--out-dir", str(out))

    meta = json.loads((out / "meta.json").read_text(encoding="utf-8"))
    assert meta["train"]["docs"] == 36 and meta["val"]["docs"] == 4
    import numpy as np
    for split, expect in (("train", [d for i, d in enumerate(docs) if i % 10]),
                          ("val", [docs[i] for i in range(0, 40, 10)])):
        ids = np.fromfile(out / f"{split}.bin", dtype=np.uint16).tolist()
        assert len(ids) == meta[split]["tokens"]
        bos, eos = tok.special_tokens["<bos>"], tok.special_tokens["<eos>"]
        got, cur = [], []
        for t in ids:                                             # tách lại từng bài theo bos/eos
            if t == bos:
                cur = []
            elif t == eos:
                got.append(tok.decode(cur))
            else:
                cur.append(t)
        assert got == expect                                      # roundtrip đúng, đúng thứ tự


def test_token_file_dataset_shift_by_one(tmp_path):
    import numpy as np
    np.arange(21, dtype=np.uint16).tofile(tmp_path / "t.bin")
    ds = TokenFileDataset(str(tmp_path / "t.bin"), context_len=5)
    assert len(ds) == 4
    x, y = ds[1]
    assert x.tolist() == [5, 6, 7, 8, 9] and y.tolist() == [6, 7, 8, 9, 10]
    assert x.dtype == torch.int64


def test_ppl_metric_of_uniform_model_equals_vocab():
    """Logit bằng nhau → CE = ln V → perplexity đúng bằng V. Lệch là công thức sai (vd trung bình
    theo batch rồi mới exp, hay quên reduction='sum')."""
    from ai_core.scripts.train import _ppl_metric

    class Uniform(torch.nn.Module):
        def forward(self, x):
            return torch.zeros(*x.shape, 37), None

    data = [(torch.randint(0, 37, (2, 8)), torch.randint(0, 37, (2, 8))) for _ in range(3)]
    ppl = _ppl_metric(max_batches=10)(Uniform(), data, torch.device("cpu"))
    assert math.isclose(ppl, 37, rel_tol=1e-5)
