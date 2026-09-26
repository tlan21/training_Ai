"""Settings inference-service — env-driven, khớp master plan §2.4."""

import os
from dataclasses import dataclass, field


def _load_dotenv() -> None:
    """Nạp .env (nếu có) vào os.environ — không ghi đè biến đã set sẵn. Không cần lib ngoài.
    Tìm .env ở thư mục inference-service (cha của app/)."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(root, ".env")
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key, val = key.strip(), val.strip().strip('"').strip("'")
            os.environ.setdefault(key, val)   # env thật ưu tiên hơn .env


def _checkpoint_dir() -> str:
    value = os.environ.get("CHECKPOINT_DIR", "../ai-core/checkpoints")
    if os.path.isabs(value):
        return value
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.abspath(os.path.join(root, value))


_load_dotenv()


@dataclass
class Settings:
    host: str = "0.0.0.0"
    port: int = 8001
    # Bearer key format sk-local-... (master plan §2.4). Đặt qua env cả service lẫn gateway.
    ai_service_key: str = field(default_factory=lambda: os.environ.get("AI_SERVICE_KEY", "sk-local-dev-key"))
    # Thư mục checkpoint từ ai-core (best.pt mỗi model). Thiếu file → endpoint chạy STUB.
    checkpoint_dir: str = field(default_factory=_checkpoint_dir)
    device: str = field(default_factory=lambda: os.environ.get("INFER_DEVICE", "auto"))  # auto|cpu|cuda
    # Bật buộc stub kể cả khi có checkpoint (dev/test không GPU)
    force_stub: bool = field(default_factory=lambda: os.environ.get("FORCE_STUB", "0") == "1")
    # Milvus cho /v1/recommendation (T1.7d). Không kết nối được → endpoint rơi về stub, không sập.
    milvus_host: str = field(default_factory=lambda: os.environ.get("MILVUS_HOST", "localhost"))
    milvus_port: str = field(default_factory=lambda: os.environ.get("MILVUS_PORT", "19530"))
    milvus_collection: str = field(default_factory=lambda: os.environ.get(
        "MILVUS_RECO_COLLECTION", "user_recommendation_embeddings"))


settings = Settings()


def resolve_device(device: str) -> str:
    if device != "auto":
        return device
    try:
        import torch
        return "cuda" if torch.cuda.is_available() else "cpu"
    except Exception:
        return "cpu"
