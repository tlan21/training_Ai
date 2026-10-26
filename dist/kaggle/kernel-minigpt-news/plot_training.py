"""Export loss and held-out validation curves from the downloaded TensorBoard logs."""

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from tensorboard.backend.event_processing.event_accumulator import EventAccumulator

ROOT = Path(__file__).resolve().parents[3]
RUN = Path("D:/data_training_ai/minigpt_news/output-v2/news_run")
val = [json.loads(row) for row in (RUN / "validation.jsonl").read_text().splitlines()]
assert len(val) == 20
fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), layout="constrained")
for stage, offset, expected, color in (("clean", 0, 16000, "#461599"), ("asr", 16000, 4000, "#057A71")):
    events = EventAccumulator(str(RUN / "runs" / stage / "minigpt"), size_guidance={"scalars": 0})
    events.Reload()
    losses = events.Scalars("train/loss")
    assert len(losses) == expected and all(np.isfinite(row.value) for row in losses)
    x = np.array([row.step + offset + 1 for row in losses])
    y = np.array([row.value for row in losses])
    axes[0].plot(x[::20], y[::20], color=color, alpha=.17)
    axes[0].plot(x[199:], np.convolve(y, np.ones(200)/200, mode="valid"), color=color, label=f"{stage}: mean 200 steps")
x = np.arange(1000, 21000, 1000)
axes[1].plot(x, [r["clean_rouge_l"] for r in val], label="Clean validation", color="#461599")
axes[1].plot(x, [r["asr_rouge_l"] for r in val], label="Synthetic ASR validation", color="#057A71")
axes[1].plot(x, [(r["clean_rouge_l"]+r["asr_rouge_l"])/2 for r in val], "--", label="Selection mean", color="#D85D00")
axes[1].axhline(val[0]["lead1_clean"], color="#666666", linestyle=":", label="Lead-1 (clean subset)")
axes[1].scatter([19000], [.20128670785550362], color="#D85D00", marker="*", s=140, zorder=4)
for ax in axes:
    ax.axvline(16000, color="#777777", linestyle="--", alpha=.6)
    ax.set_xlabel("Training step (ASR stage offset by 16000)")
    ax.grid(alpha=.15)
    ax.legend(fontsize=8)
axes[0].set(title="Training loss (raw faint / moving mean)", ylabel="Target cross-entropy")
axes[1].set(title="Validation only; star = selected ASR step 3000", ylabel="Word ROUGE-L F1")
fig.suptitle("MiniGPT News: ASR starts from clean best (step 7000), not clean last")
for suffix in ("png", "svg"):
    fig.savefig(ROOT / f"docs/T1.6c_news_curves.{suffix}", dpi=160)
print("20k loss scalars finite; curves exported")
