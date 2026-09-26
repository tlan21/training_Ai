"""ai_core — thuật toán AI nguyên thủy tự code (primitives, optim, tokenizer, 6 model)."""

from .config import ModelConfig, TrainConfig

__version__ = "0.1.0"


def build_model(name: str, cfg: ModelConfig):
    """Factory dựng model theo tên. Model được thêm dần ở T1.3–T1.7."""
    if name == "vit":
        from .models.vit import ViT
        return ViT(cfg)
    if name == "siamese":
        from .models.siamese import SiameseViT
        return SiameseViT(cfg)
    if name == "asr_ctc":
        from .models.asr_ctc import ASR_CTC
        return ASR_CTC(cfg)
    if name == "highlight_fusion":
        from .models.highlight_fusion import HighlightFusion
        return HighlightFusion(cfg)
    if name == "minigpt":
        from .models.minigpt import MiniGPT
        return MiniGPT(cfg)
    if name == "two_tower":
        from .models.two_tower import TwoTower
        return TwoTower(cfg, user_dim=cfg.user_dim, video_dim=cfg.video_dim)
    raise ValueError(f"Model chưa hỗ trợ: {name}")


__all__ = ["ModelConfig", "TrainConfig", "build_model", "__version__"]
