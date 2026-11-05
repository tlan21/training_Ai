"""AI-26: build the syllable bigram LM for CTC decoding from public text already in the project (no external model).

  python -m ai_core.scripts.build_syllable_lm --news D:/data_training_ai/minigpt_news/dataset/news_train.json \
      --vivos D:/data_training_ai/data/manifests/vivos.json --out D:/data_training_ai/asr_lm_v1

News = Binhvq train split used for MiniGPT (football-keyword articles first, then general, up to --articles);
VIVOS = train-split transcripts only (VIVOS test stays unseen).
"""
import argparse
import hashlib
import json
from pathlib import Path

from ..models.ctc_lm import SyllableLM, syllables
from .prepare_football_summary import FOOTBALL


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--news", required=True)
    p.add_argument("--vivos", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--articles", type=int, default=30000)
    args = p.parse_args()
    news = json.loads(Path(args.news).read_text(encoding="utf-8"))
    football = [a for a in news if FOOTBALL.search(a["title"] + " " + a["summary"])]
    chosen = (football + [a for a in news if not FOOTBALL.search(a["title"] + " " + a["summary"])])[:args.articles]
    del news
    sentences = [s for a in chosen for s in syllables(a["title"] + ". " + a["summary"] + ". " + a["body"])]
    vivos = [i["extra"]["transcript"] for i in json.loads(Path(args.vivos).read_text(encoding="utf-8"))["items"] if i["split"] == "train"]
    sentences += [s for t in vivos for s in syllables(t)]
    lm = SyllableLM.train(sentences)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    lm.save(out / "lm.json")
    sha = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
    manifest = {"sources": {"news": args.news, "news_sha256": sha(args.news), "vivos": args.vivos, "vivos_sha256": sha(args.vivos)},
                "articles": len(chosen), "football_articles": min(len(football), len(chosen)), "vivos_train_utterances": len(vivos),
                "tokens": sum(map(len, sentences)), "unigrams": len(lm.unigram), "bigram_contexts": len(lm.bigram),
                "bigrams": sum(map(len, lm.bigram.values())), "min_counts": {"unigram": 2, "bigram": 2}, "discount": lm.d,
                "lm_sha256": sha(out / "lm.json")}
    (out / "lm_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False))


if __name__ == "__main__":
    main()
