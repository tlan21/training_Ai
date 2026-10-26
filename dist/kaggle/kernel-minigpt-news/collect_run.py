"""Watch the authorized private run and collect its verified result; never auto-deploy."""

import hashlib
import json
import time
from pathlib import Path

from kaggle.api.kaggle_api_extended import KaggleApi

ROOT = Path(__file__).resolve().parents[3]
OUTPUT = Path("D:/data_training_ai/minigpt_news/output-v2")
KERNEL = "traininghighlight/ai-core-minigpt-news"


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    api = KaggleApi()
    api.authenticate()
    while True:
        status = api.kernels_status(KERNEL).status.name
        (OUTPUT / "watch_status.json").write_text(json.dumps({"kernel": KERNEL, "status": status,
                                                              "checked_at_unix": time.time()}))
        print(time.strftime("%Y-%m-%d %H:%M:%S"), status, flush=True)
        if status in ("COMPLETE", "ERROR", "CANCEL_ACKNOWLEDGED"):
            break
        time.sleep(60)
    token = None
    while True:
        _, token = api.kernels_output(KERNEL, path=str(OUTPUT), force=True, quiet=True, page_token=token)
        if not token:
            break
    if status != "COMPLETE":
        raise SystemExit("Training did not complete; check the collected kernel log")
    reports = list(OUTPUT.rglob("news_eval.json"))
    assert len(reports) == 1, "missing or ambiguous final evaluation"
    report = json.loads(reports[0].read_text(encoding="utf-8"))
    assert report["n_test"] == 1000
    assert abs(report["delta"] - (report["rouge_l"] - report["lead1_rouge_l"])) < 1e-8
    checkpoint = reports[0].parent / "minigpt/best.pt"
    assert hashlib.sha1(checkpoint.read_bytes()).hexdigest() == report["checkpoint_sha1"]
    expected = json.loads((ROOT / "data/manifests/minigpt_news_dataset.json").read_text(encoding="utf-8"))
    assert report["dataset"]["splits"] == expected["splits"], "frozen split changed"
    (ROOT / "docs/T1.6c_news_metrics.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print("FINAL", json.dumps({k: report[k] for k in ("rouge_l", "lead1_rouge_l", "delta", "delta_ci95",
                                                    "automatic_threshold_pass", "human_evaluation")}), flush=True)
    print("Checkpoint collected and verified; deployment and human evaluation remain pending.", flush=True)


if __name__ == "__main__":
    main()
