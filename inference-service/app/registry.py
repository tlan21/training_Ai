"""Model registry: nạp 6 checkpoint thật từ ai-core, hoặc STUB khi thiếu file/torch/GPU.

Master plan §2.4: 1 process nạp cả 6 model (~120MB fp16). Thiếu checkpoint → endpoint
vẫn trả đúng schema (mock) để backend/UI code song song trước khi AI train xong.
"""

import os
import sys

from .config import resolve_device, settings

_MODEL_FILES = {
    "vit": "vit/best.pt",
    "siamese": "siamese/best.pt",
    "asr_ctc": "asr_ctc/best.pt",
    "highlight_fusion": "highlight_fusion/best.pt",
    "minigpt": "minigpt/best.pt",
    "two_tower": "two_tower/best.pt",
}


class ModelRegistry:
    def __init__(self) -> None:
        self.device = resolve_device(settings.device)
        self.models: dict[str, object] = {}      # name → model đã .eval() (chỉ khi real)
        self.tokenizer = None                     # BPE cho minigpt (real)
        self.asr_vocab: list[str] | None = None   # char vocab cho ASR (index 0 = blank)
        self.vit_classes: list[str] | None = None # tên danh mục ViT (theo class index)
        self.loaded: list[str] = []               # tên model nạp THẬT
        self.degraded: set[str] = set()           # model nạp thật nhưng real path lỗi → đang trả stub
        self.stub_mode = True
        self.load_error: str | None = None

    @property
    def model_dtype(self):
        """dtype trọng số model đã nạp (half trên CUDA, float32 trên CPU) — để cast input khớp."""
        import torch
        return torch.float16 if self.device == "cuda" else torch.float32

    def mark_degraded(self, name: str) -> None:
        self.degraded.add(name)

    def _ensure_ai_core_on_path(self) -> bool:
        try:
            import ai_core  # noqa: F401
            return True
        except ImportError:
            here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            ai_core_root = os.path.abspath(os.path.join(here, "..", "ai-core"))
            if os.path.isdir(ai_core_root):
                sys.path.insert(0, ai_core_root)
            try:
                import ai_core  # noqa: F401
                return True
            except ImportError:
                return False

    def load_all(self) -> None:
        """Thử nạp thật; bất kỳ lỗi nào → giữ stub cho model đó."""
        self.models.clear()
        self.loaded.clear()
        self.degraded.clear()
        self.load_error = None
        if settings.force_stub or not self._ensure_ai_core_on_path():
            self.stub_mode = True
            self.load_error = "stub forced or ai-core unavailable"
            return
        try:
            import torch
            from ai_core import build_model
            from ai_core.config import ModelConfig
            from ai_core.training.checkpoint import load_checkpoint
        except Exception:
            self.stub_mode = True
            self.load_error = "torch/ai-core import failed"
            return

        for name, rel in _MODEL_FILES.items():
            path = os.path.join(settings.checkpoint_dir, rel)
            if not os.path.exists(path):
                last = os.path.join(settings.checkpoint_dir, os.path.dirname(rel), "last.pt")
                if os.path.exists(last):
                    path = last          # fallback last.pt khi chưa có best.pt
                else:
                    continue
            try:
                ckpt = load_checkpoint(path, map_location=self.device)
                cfg = ModelConfig(**ckpt["config"])
                model = build_model(cfg.name, cfg)
                model.load_state_dict(ckpt["state_dict"])
                model.eval().to(self.device)
                if self.device == "cuda":
                    model.half()
                self.models[name] = model
                self.loaded.append(name)
                metadata = ckpt.get("metadata") or {}
                if name == "minigpt" and (ckpt.get("bpe_vocab") or metadata.get("bpe_vocab")):
                    self.tokenizer = self._rebuild_tokenizer(ckpt.get("bpe_vocab") or metadata["bpe_vocab"])
                if name == "asr_ctc":
                    self.asr_vocab = ckpt.get("char_vocab") or metadata.get("char_vocab") or self._load_sidecar(rel, "vocab.json")
                if name == "vit":
                    self.vit_classes = ckpt.get("classes") or metadata.get("classes") or self._load_sidecar(rel, "classes.json")
            except Exception as e:  # noqa: BLE001
                print(f"[registry] nạp {name} lỗi ({e}) → stub cho model này")

        self.stub_mode = len(self.loaded) < len(_MODEL_FILES)
        if self.stub_mode:
            missing = sorted(set(_MODEL_FILES) - set(self.loaded))
            self.load_error = f"missing or invalid checkpoints: {', '.join(missing)}"

    def _load_sidecar(self, model_rel: str, fname: str):
        """Đọc file JSON cạnh checkpoint (vd checkpoints/asr_ctc/vocab.json). None nếu không có."""
        import json
        path = os.path.join(settings.checkpoint_dir, os.path.dirname(model_rel), fname)
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        return None

    @staticmethod
    def _rebuild_tokenizer(bpe_vocab: dict):
        from ai_core.tokenizer import BPETokenizer
        tok = BPETokenizer(vocab_size=bpe_vocab.get("vocab_size", 8192))
        tok.special_tokens = {k: int(v) for k, v in bpe_vocab["special_tokens"].items()}
        for i, (a, b) in enumerate(bpe_vocab["merges"]):
            new_id = 260 + i
            tok.merges[(a, b)] = new_id
            tok._token_bytes[new_id] = tok._token_bytes[a] + tok._token_bytes[b]
        return tok

    def is_real(self, name: str) -> bool:
        return name in self.models

    def gpu_stats(self) -> tuple[float, float]:
        """(vram_used_MB, gpu_util_%). Non-CUDA → (0,0)."""
        if self.device != "cuda":
            return 0.0, 0.0
        try:
            import torch
            vram = torch.cuda.memory_allocated() / (1024 ** 2)
            util = 0.0
            try:
                import pynvml
                pynvml.nvmlInit()
                h = pynvml.nvmlDeviceGetHandleByIndex(0)
                util = float(pynvml.nvmlDeviceGetUtilizationRates(h).gpu)
            except Exception:
                pass
            return vram, util
        except Exception:
            return 0.0, 0.0


registry = ModelRegistry()
