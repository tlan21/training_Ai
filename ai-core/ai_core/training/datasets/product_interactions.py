"""AI-12a/12c — product interaction export (Codex INT-13) → validated, labelled, time-split data for Two-Tower v2.

Data contract: coordination/claude/api/TWO_TOWER_V2_DATA_CONTRACT.md. Gate stages: user decision D19.
Product IDs stay the keys (no hashing / modulo / reuse of training IDs); MovieLens-style numeric IDs are rejected.
"""

import hashlib
import json
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

# v1.1: manifest.provenance required + per-field schema check (HC-09). No bundle in v1 was ever produced.
EXPORT_VERSION = "ttv2-data-v1.1"
REJECT_REASONS = ("bad_id_format", "unknown_user", "unknown_video", "bad_type", "bad_timestamp", "after_snapshot",
                  "before_user_created", "video_not_visible", "clip_video_mismatch", "bad_duration")
_STR, _NUM, _OPT = (str,), (int, float), (str, type(None))
SCHEMA = {
    "users.jsonl": {"user_id": _STR, "created_at": _STR, "preferred_category_ids": (list,)},
    "categories.jsonl": {"category_id": _STR, "name": _STR},
    "videos.jsonl": {"video_id": _STR, "category_id": _OPT, "duration_seconds": _NUM, "visible_to_client": (bool,), "created_at": _STR},
    "clips.jsonl": {"clip_id": _STR, "video_id": _STR, "start_time": _NUM, "end_time": _NUM, "status": _STR},
    "interactions.jsonl": {"interaction_id": (int,), "user_id": _STR, "video_id": _STR, "clip_id": _OPT,
                           "interaction_type": _STR, "duration_watched": (int,), "created_at": _STR},
}
PROVENANCE_KEYS = ("source", "exporter", "environment")
# v2: watch rules made mutually exclusive — v1 called ≥30 s positive even when it was <10% of a long video.
LABEL_VERSION = "ttv2-labels-v2"
FILES = ("users.jsonl", "categories.jsonl", "videos.jsonl", "clips.jsonl", "interactions.jsonl")
TYPES = {"click", "watch_time", "like", "share", "skip", "save"}
EXPLICIT_POSITIVE = {"like", "share", "save"}
POSITIVE_RATIO, POSITIVE_SECONDS, NEGATIVE_RATIO = 0.5, 30.0, 0.1
DEDUP_WINDOW = timedelta(seconds=30)
_ID = {p: re.compile(rf"{p}_[A-Za-z0-9_]{{1,46}}") for p in ("usr", "vid", "clp", "cat")}


def parse_ts(value: str) -> datetime:
    ts = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if ts.tzinfo is None:
        raise ValueError(f"timestamp without timezone: {value}")
    return ts.astimezone(timezone.utc)


@dataclass
class Export:
    users: dict
    categories: list
    videos: dict
    clips: dict
    interactions: list
    snapshot_at: datetime
    provenance: dict | None = None


def _check_schema(name: str, rows: list) -> None:
    """Shape errors mean a broken exporter, not bad user behaviour → fail the whole bundle instead of dropping rows."""
    for n, row in enumerate(rows, 1):
        for key, types in SCHEMA[name].items():
            if key not in row:
                raise ValueError(f"{name} line {n}: missing field {key}")
            value = row[key]
            if not isinstance(value, types) or (isinstance(value, bool) and bool not in types):
                raise ValueError(f"{name} line {n}: field {key} has type {type(value).__name__}")


def load_export(directory) -> Export:
    """Read one export bundle: version, provenance, row count + sha256 per file, then per-field schema."""
    root = Path(directory)
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("export_version") != EXPORT_VERSION:
        raise ValueError(f"export_version {manifest.get('export_version')!r} != {EXPORT_VERSION}")
    prov = manifest.get("provenance")
    if not isinstance(prov, dict) or not all(isinstance(prov.get(k), str) and prov[k] for k in PROVENANCE_KEYS):
        raise ValueError(f"manifest.provenance must have non-empty {PROVENANCE_KEYS}")
    rows = {}
    for name in FILES:
        data = (root / name).read_bytes()
        meta = manifest["files"][name]
        if hashlib.sha256(data).hexdigest() != meta["sha256"]:
            raise ValueError(f"{name}: sha256 mismatch with manifest")
        rows[name] = [json.loads(line) for line in data.decode("utf-8").splitlines() if line.strip()]
        if len(rows[name]) != meta["rows"]:
            raise ValueError(f"{name}: {len(rows[name])} rows, manifest says {meta['rows']}")
        _check_schema(name, rows[name])
    return Export(
        users={u["user_id"]: u for u in rows["users.jsonl"]},
        categories=rows["categories.jsonl"],
        videos={v["video_id"]: v for v in rows["videos.jsonl"]},
        clips={c["clip_id"]: c for c in rows["clips.jsonl"]},
        interactions=rows["interactions.jsonl"],
        snapshot_at=parse_ts(manifest["snapshot_at"]),
        provenance=prov,
    )


@dataclass
class Cleaned:
    export: Export
    interactions: list
    dropped: dict = field(default_factory=dict)


def item_seconds(export: Export, row: dict) -> float:
    """Watch ratio denominator: the clip shown in the feed, else the whole video."""
    if row.get("clip_id"):
        clip = export.clips[row["clip_id"]]
        return float(clip["end_time"]) - float(clip["start_time"])
    return float(export.videos[row["video_id"]]["duration_seconds"])


def _reject_reason(export: Export, row: dict) -> str | None:
    if not (_ID["usr"].fullmatch(str(row.get("user_id"))) and _ID["vid"].fullmatch(str(row.get("video_id")))):
        return "bad_id_format"
    user, video = export.users.get(row["user_id"]), export.videos.get(row["video_id"])
    if user is None:
        return "unknown_user"
    if video is None:
        return "unknown_video"
    if row.get("interaction_type") not in TYPES:
        return "bad_type"
    try:
        at = parse_ts(row["created_at"])
    except (KeyError, TypeError, ValueError):
        return "bad_timestamp"
    if at > export.snapshot_at:
        return "after_snapshot"
    if at < parse_ts(user["created_at"]):
        return "before_user_created"
    if not video.get("visible_to_client"):
        return "video_not_visible"
    clip_id = row.get("clip_id")
    if clip_id and (clip_id not in export.clips or export.clips[clip_id]["video_id"] != row["video_id"]):
        return "clip_video_mismatch"
    watched = row.get("duration_watched") or 0
    if watched < 0 or (row["interaction_type"] == "watch_time" and watched > 1.5 * item_seconds(export, row) + 5):
        return "bad_duration"
    return None


def clean(export: Export) -> Cleaned:
    """Drop invalid rows (counted per reason), then collapse repeats of the same event within DEDUP_WINDOW."""
    dropped, valid = Counter(), []
    for row in export.interactions:
        reason = _reject_reason(export, row)
        if reason:
            dropped[reason] += 1
        else:
            valid.append({**row, "_at": parse_ts(row["created_at"])})
    valid.sort(key=lambda r: (r["_at"], r["interaction_id"]))
    kept, last = [], {}
    for row in valid:
        key = (row["user_id"], row["video_id"], row.get("clip_id"), row["interaction_type"])
        prev = last.get(key)
        if prev is not None and row["_at"] - prev["_at"] <= DEDUP_WINDOW:
            dropped["duplicate"] += 1
            prev["duration_watched"] = max(prev.get("duration_watched") or 0, row.get("duration_watched") or 0)
            continue
        last[key] = row
        kept.append(row)
    return Cleaned(export, kept, dict(dropped))


@dataclass(frozen=True)
class Label:
    user_id: str
    video_id: str
    positive: bool
    at: datetime


def _signal(export: Export, row: dict) -> bool | None:
    """True = positive, False = explicit negative, None = no label (click, partial watch)."""
    kind = row["interaction_type"]
    if kind in EXPLICIT_POSITIVE:
        return True
    if kind == "skip":
        return False
    if kind == "watch_time":
        watched = float(row.get("duration_watched") or 0)
        ratio = watched / max(item_seconds(export, row), 1e-9)
        # Positive needs ratio ≥ 10% in every branch, negative needs < 10%: no watch can be both.
        if ratio >= POSITIVE_RATIO or (watched >= POSITIVE_SECONDS and ratio >= NEGATIVE_RATIO):
            return True
        if ratio < NEGATIVE_RATIO and watched < POSITIVE_SECONDS:
            return False
    return None


def label(cleaned: Cleaned) -> list[Label]:
    """One label per (user, video): any positive wins, dated at its first positive event."""
    first: dict = {}
    for row in cleaned.interactions:  # already time-sorted
        sig = _signal(cleaned.export, row)
        if sig is None:
            continue
        key = (row["user_id"], row["video_id"])
        cur = first.get(key)
        if cur is None or (sig and not cur.positive):
            first[key] = Label(row["user_id"], row["video_id"], sig, row["_at"])
    return sorted(first.values(), key=lambda l: (l.at, l.user_id, l.video_id))


@dataclass
class Split:
    train: list
    eval: list
    cutoff: datetime
    cold_start_users: set


def time_split(labels: list[Label], eval_fraction: float = 0.2) -> Split:
    """Global time cutoff: everything at/after it is eval, so no eval event precedes a train event (no leakage)."""
    if not labels:
        raise ValueError("no labels to split")
    times = sorted(l.at for l in labels)
    cutoff = times[min(len(times) - 1, int(len(times) * (1 - eval_fraction)))]
    train = [l for l in labels if l.at < cutoff]
    evals = [l for l in labels if l.at >= cutoff]
    warm = {l.user_id for l in train if l.positive}
    return Split(train, evals, cutoff, {l.user_id for l in evals if l.positive} - warm)


@dataclass
class Vocab:
    ids: list
    version: str

    def index(self, category_id):
        return self.ids.index(category_id) if category_id in self.ids else None


def category_vocab(export: Export) -> Vocab:
    """Sorted product category IDs; the version hash goes into the model artifact manifest."""
    ids = sorted(c["category_id"] for c in export.categories)
    return Vocab(ids, hashlib.sha256("\n".join(ids).encode()).hexdigest()[:12])


def gate_stage(n_users: int, n_valid: int, eval_users_with_5_pos: int) -> str:
    """D19 data stages; PRODUCTION_READY additionally needs metrics vs Popularity and is decided at evaluation time."""
    if n_users >= 200 and n_valid >= 5000 and eval_users_with_5_pos > 0:
        return "EVAL_READY"
    return "TRAIN_EXPERIMENTAL"
