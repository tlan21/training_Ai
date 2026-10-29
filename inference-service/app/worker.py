"""Model worker (D24): pure inference on the 6 checkpoints — bytes/vectors/text in, labels/vectors/text out.

No MinIO/Milvus/HTTP here; the facade (services.py, visual_index.py) owns every I/O. The same functions run
in-process (default) or behind worker_app.py when MODEL_WORKER_URL points to a remote worker.
Inputs: images = encoded JPEG/PNG/WebP bytes; pcm = float32 little-endian mono 16 kHz samples.
Outputs are plain JSON types so the remote path returns exactly what the in-process path returns.
"""

import io

from .registry import registry


class InvalidInput(ValueError):
    """Request content the model cannot use (unreadable image/audio, wrong feature shape) — not a model failure."""


def decode_image(data: bytes, img_size: int = 224):
    """Encoded image → tensor (3, H, W) in [0, 1]."""
    import numpy as np
    import torch
    from PIL import Image
    try:
        img = Image.open(io.BytesIO(data))
        if img.width * img.height > 20_000_000:
            raise ValueError("Image exceeds 20 megapixels")
        img = img.convert("RGB").resize((img_size, img_size))
    except (OSError, ValueError) as e:
        raise InvalidInput(f"keyframe không đọc được (JPEG/PNG/WebP ≤20 MP): {type(e).__name__}: {e}") from e
    return torch.from_numpy(np.asarray(img)).float().div(255.0).permute(2, 0, 1)


def vision(images: list[bytes]):
    """ViT → [category, 256-d embedding per frame, {class: summed logit}] (sums add up across batches of one video)."""
    import torch
    model = registry.models["vit"]
    if not images:
        raise InvalidInput("empty keyframes")
    embeddings, total_logits = [], None
    with torch.no_grad():
        for start in range(0, len(images), 16):
            imgs = torch.stack([decode_image(b) for b in images[start:start+16]]).to(device=registry.device, dtype=registry.model_dtype)
            logits, emb = model(imgs, return_embedding=True)
            summed = logits.float().sum(0)
            total_logits = summed if total_logits is None else total_logits + summed
            embeddings.extend(emb.float().cpu().tolist())
    idx = int(total_logits.argmax().item())
    classes = registry.vit_classes
    names = [classes[i] if classes and i < len(classes) else f"class_{i}" for i in range(len(total_logits))]
    return [names[idx], embeddings, {name: float(x) for name, x in zip(names, total_logits)}]


def siamese(images: list[bytes]) -> list[list[float]]:
    """Siamese → one L2-normalised 128-d vector per image (database_schema §4.1)."""
    import torch
    if not images:
        raise InvalidInput("No images to encode")
    frames = [decode_image(b) for b in images]   # bad input is a 422 even when the model is missing
    if not registry.is_real("siamese"):
        raise RuntimeError("Siamese checkpoint is not loaded")
    with torch.inference_mode():
        batch = torch.stack(frames).to(device=registry.device, dtype=registry.model_dtype)
        vectors = registry.models["siamese"].encode(batch).float().cpu()
    if vectors.shape[1] != 128 or not torch.isfinite(vectors).all():
        raise ValueError("Invalid Siamese embeddings")
    return vectors.tolist()


_LEGACY_CLIP_RULES = {"threshold": 75.0, "merge_gap_seconds": 0, "min_clip_seconds": 1, "min_video_seconds": 0}


def _window_scores(model, v, a, window: int, stride: int):
    """Same as ai_core.scripts.eval_highlight.model_scores_overlap (the DoD scoring), but on the model's device/dtype:
    windows every `stride` s, last one flush with the end, each second = mean of the windows covering it."""
    import torch
    n = v.shape[0]
    if n <= window:                               # eval model_scores: zero-pad one window, drop the padding
        pad = window - n
        v, a = torch.cat([v, v.new_zeros(pad, v.shape[1])]), torch.cat([a, a.new_zeros(pad, a.shape[1])])
        return model(v[None], a[None])[0, :n].float()
    starts = list(range(0, n - window + 1, stride))
    if starts[-1] + window < n:
        starts.append(n - window)
    acc = torch.zeros(n, device=v.device)
    cnt = torch.zeros(n, device=v.device)
    for s0 in starts:
        acc[s0:s0 + window] += model(v[None, s0:s0 + window], a[None, s0:s0 + window])[0].float()
        cnt[s0:s0 + window] += 1
    return acc / cnt


def highlight(vision: list[list[float]], audio: list[list[float]]) -> dict:
    """Fusion → {"scores": per-second 0–100, "clip_rules": {threshold 0–100, merge_gap_seconds, min_clip_seconds}}.

    With `highlight_fusion/postproc.json` (AI-16) this is exactly the evaluated DoD recipe: seed ensemble (mean),
    overlapping windows, moving average k, τ. Without it: the legacy single-model path, unchanged."""
    import torch
    import torch.nn.functional as F
    model = registry.models["highlight_fusion"]
    dt = registry.model_dtype                     # khớp dtype model (half trên CUDA) để tránh mismatch
    if len(vision) != len(audio):
        raise InvalidInput("vision_embeddings và audio_spectrogram_features phải cùng số giây")
    if not vision:
        raise InvalidInput("empty highlight features")
    if any(len(v) != 256 for v in vision) or any(len(a) != 64 for a in audio):
        raise InvalidInput("highlight features phải là vision 256-d và audio 64-d")
    window = 120  # Same window length used to train the Fusion checkpoint.
    recipe = registry.highlight_postproc
    with torch.no_grad():
        if not recipe:
            scores = []
            for start in range(0, len(vision), window):
                v = torch.tensor([vision[start:start+window]], device=registry.device, dtype=dt)
                a = torch.tensor([audio[start:start+window]], device=registry.device, dtype=dt)
                scores.extend(round(float(x) * 100, 1) for x in model(v, a)[0])
            return {"scores": scores, "clip_rules": dict(_LEGACY_CLIP_RULES)}
        v, a = torch.tensor(vision), torch.tensor(audio)
        if recipe.get("feature_norm") == "per_video":   # AI-17: the request is the whole video, as at training
            from ai_core.training.datasets.highlight_dataset import normalize_per_video
            v, a = normalize_per_video(v), normalize_per_video(a)
        v, a = v.to(device=registry.device, dtype=dt), a.to(device=registry.device, dtype=dt)
        mean = torch.stack([_window_scores(m, v, a, window, recipe["stride"]) for m in registry.highlight_members]).mean(0)
        k = recipe["smooth_k"]
        if k > 1:                                 # eval_highlight.smooth: replicate edges, moving average
            mean = F.avg_pool1d(F.pad(mean[None, None], (k // 2, k // 2), mode="replicate"), k, stride=1)[0, 0]
    return {"scores": [round(float(x) * 100, 1) for x in mean.cpu()],
            "clip_rules": {"threshold": recipe["tau"] * 100, "merge_gap_seconds": recipe.get("merge_gap_seconds", 0),
                           "min_clip_seconds": recipe.get("min_clip_seconds", 1),
                           "min_video_seconds": recipe.get("min_video_seconds", 0)}}


def asr(pcm: bytes):
    """CTC on one ≤20 s chunk → [text, [{start, end, text, confidence}]] with chunk-relative times."""
    import torch
    from ai_core.audio.mel import log_mel_spectrogram
    from ai_core.models.ctc import ctc_greedy_decode, ctc_segments
    if not pcm or len(pcm) % 4:
        raise InvalidInput("pcm must be non-empty float32 samples")
    signal = torch.frombuffer(bytearray(pcm), dtype=torch.float32)
    vocab = registry.asr_vocab
    if vocab is None:
        raise NotImplementedError("thiếu char_vocab cho ASR (checkpoints/asr_ctc/vocab.json)")
    model = registry.models["asr_ctc"]
    mel = log_mel_spectrogram(signal, n_mels=80, sr=16000).unsqueeze(0).to(
        device=registry.device, dtype=registry.model_dtype)          # khớp dtype model
    lengths = torch.tensor([mel.shape[2]], device=registry.device)
    with torch.no_grad():
        log_probs, out_len = model(mel, lengths)         # (1, T', C)
    lp = log_probs.float().cpu()
    valid = int(out_len[0].item())                       # bỏ frame padding khi tính conf
    ids = ctc_greedy_decode(lp, out_len.cpu(), blank=0)[0]
    text = "".join(vocab[i] for i in ids if 0 < i < len(vocab))
    conf = float(lp[0, :valid].max(-1).values.exp().mean()) if valid > 0 else 0.0

    # Timestamp THẬT từ alignment CTC. Bản trước trả đúng một segment 0 → len(audio): khớp schema,
    # trông như chạy được, nhưng không dựng nổi phụ đề vì mọi dòng cùng một mốc thời gian.
    # frame_sec = hop/sr × subsample; suy subsample từ chính đầu ra model để encoder đổi tỉ lệ thì
    # timestamp không lệch âm thầm.
    subsample = mel.shape[2] / max(valid, 1)
    parts = ctc_segments(lp[0], valid, vocab, 160 / 16000 * subsample, blank=0)
    dur = round(signal.numel() / 16000, 2)
    if not parts:
        parts = [{"start": 0.0, "end": dur, "text": text}]
    return [text, [{"start": p["start"], "end": min(p["end"], dur), "text": p["text"], "confidence": round(conf, 3)}
                   for p in parts]]


def summarize(prompt: str, max_tokens: int, temperature: float) -> str:
    """Use the trained EOS-delimited formats; recursively reduce all long-input chunks."""
    import torch
    from ai_core.training.datasets.summary_dataset import CONTROL_TOKENS

    model = registry.models["minigpt"]
    tok = registry.tokenizer
    if tok is None:
        raise RuntimeError("minigpt checkpoint thiếu BPE vocabulary")
    eos = tok.special_tokens["<eos>"]
    context = int(registry.minigpt_metadata.get("summary_context_len", 512))
    reserve = int(registry.minigpt_metadata.get("max_target_tokens", 96))
    if not 1 < reserve < context <= model.cfg.context_len:
        raise RuntimeError("invalid MiniGPT summary context/output metadata")
    source, fmt = prompt.strip(), "sum"
    for name, marker in CONTROL_TOKENS.items():
        if source == marker or source.startswith(marker + " ") or source.startswith(marker + "\n"):
            fmt, source = name, source[len(marker):].strip()
            break
    if not source:
        return ""  # Silent audio has no transcript to summarize.
    if source.isupper():
        source = source.lower()  # Our CTC vocabulary is uppercase; ASR fine-tuning used lowercase.
    prefixes = {name: tok.encode(marker) for name, marker in CONTROL_TOKENS.items()}
    capacities = {name: context - reserve - 1 - len(prefix) for name, prefix in prefixes.items()}
    if min(capacities.values()) < 1:
        raise RuntimeError("MiniGPT context leaves no source capacity")

    def _gen(content: list[int], output_format: str, budget: int) -> str:
        prompt_ids = prefixes[output_format] + content + [eos]
        out = model.generate(
            torch.tensor([prompt_ids], device=registry.device),
            max_new_tokens=budget, temperature=temperature, eos_id=eos,
        )
        return tok.decode(out[0, len(prompt_ids):].tolist()).strip()

    # The leading space attaches to the first word in our byte BPE, exactly as in training.
    ids = tok.encode(" " + source)
    while len(ids) > capacities[fmt]:
        chunk = capacities["sum"]
        partials = [_gen(ids[i:i + chunk], "sum", reserve) for i in range(0, len(ids), chunk)]
        merged = " ".join(partials).strip()
        if not merged:
            return ""
        reduced = tok.encode(" " + merged)
        if len(reduced) >= len(ids):
            raise RuntimeError("MiniGPT map-reduce did not shrink the input")
        ids = reduced
    return _gen(ids, fmt, min(max_tokens, reserve))


def info() -> dict:
    """What the facade needs for /health when the worker is remote."""
    vram, util = registry.gpu_stats()
    return {"models_loaded": sorted(registry.loaded), "device": registry.device, "stub_mode": registry.stub_mode,
            "load_error": registry.load_error, "gpu_vram_used": vram, "gpu_util": util}


OPS = {"vision": vision, "siamese": siamese, "highlight": highlight, "asr": asr, "summarize": summarize}
