"""Pydantic request/response — khớp architecture.md §2 (5 endpoint public + vision nội bộ)."""

from pydantic import BaseModel, Field

# ---------------- /v1/completions (Summarizer, OpenAI-style) ----------------

class CompletionRequest(BaseModel):
    model: str = "primitive-gpt-summarizer"
    prompt: str
    max_tokens: int = Field(150, ge=1)
    temperature: float = Field(0.7, ge=0, le=2)
    top_p: float = 0.9
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0


class CompletionChoice(BaseModel):
    text: str
    index: int = 0
    logprobs: None = None
    finish_reason: str = "stop"


class Usage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class CompletionResponse(BaseModel):
    id: str
    object: str = "text_completion"
    created: int
    model: str
    choices: list[CompletionChoice]
    usage: Usage


# ---------------- /v1/highlight/completions (Fusion) ----------------

class HighlightFeatures(BaseModel):
    vision_embeddings: list[list[float]]
    audio_spectrogram_features: list[list[float]]


class SpeechSpan(BaseModel):
    start_time: float
    end_time: float


class HighlightRequest(BaseModel):
    model: str = "primitive-seq2seq-highlighter"
    video_id: str
    features: HighlightFeatures
    # AI-16 (optional): ASR segments of the same video (extra fields ignored) → clip edges move to sentence edges ≤3 s away.
    asr_segments: list[SpeechSpan] | None = None


class TimelineScore(BaseModel):
    second: int
    score: float                      # 0–100 (service nhân 100)


class RecommendedClip(BaseModel):
    clip_id: str
    start_time: float
    end_time: float
    average_score: float              # 0–100


class HighlightResponse(BaseModel):
    id: str
    object: str = "highlight_completion"
    created: int
    model: str
    video_id: str
    timeline_scores: list[TimelineScore]
    recommended_clips: list[RecommendedClip]
    # AI-API v1.4-rc1 (AI-17): score (0–100) above which recommended_clips were cut — draw the heatmap line here, not at a fixed 75.
    clip_threshold: float | None = None


# ---------------- ASR (ASR CTC) — response of /v2/asr/completions ----------------

class ASRSegment(BaseModel):
    id: int
    start_time: float
    end_time: float
    text: str
    confidence: float = 1.0           # 0–1 (posterior trung bình)
    warning: str | None = None        # low_confidence|blacklist


class ASRResponse(BaseModel):
    id: str
    object: str = "asr_completion"
    created: int
    model: str
    full_transcript: str
    segments: list[ASRSegment]


# ---------------- /health ----------------

class HealthResponse(BaseModel):
    status: str
    gpu_vram_used: float              # MB
    gpu_util: float                   # %
    models_loaded: list[str]
    degraded: list[str]               # model có inference lỗi thật gần nhất (input sai không tính); tự gỡ khi chạy lại được
    # AI-API v1.1: capability phụ thuộc hạ tầng → "ok" | "unavailable" | "missing_collection". Không phải lỗi model.
    dependencies: dict[str, str] = {}
    queue_depth: int
    device: str
    stub_mode: bool
    load_error: str | None = None


# ================= AI-API v2 endpoints (D24; v2.0 API_READY in release #6, v3.0 removed the /v1 storage paths) =================
# Inference only computes; the backend owns MinIO/Milvus/Postgres/Mongo.

_IMAGE_DOC = "data URI hoặc base64 JPEG/PNG/WebP (≤20 MP); không nhận path"


class VisionV2Request(BaseModel):
    model: str = "primitive-vit-classifier"
    keyframes: list[str] = Field(..., min_length=1, max_length=600, description=_IMAGE_DOC + "; nhiều hơn 600 frame → chia lô")


class VisionV2Response(BaseModel):
    id: str
    object: str = "vision_completion"
    created: int
    model: str
    category_suggestion: str                  # argmax of category_logit_sums (this request only)
    category_logit_sums: dict[str, float]     # per class, summed over frames; add across batches → argmax = whole-video category
    embeddings_256: list[list[float]]         # ViT, one per keyframe (Fusion input)
    siamese_vectors: list[list[float]]        # Siamese 128-d, L2-normalised, one per keyframe → Milvus video_frame_embeddings (COSINE)


class SearchEmbeddingRequest(BaseModel):
    model: str = "primitive-siamese-vit"
    image: str = Field(..., description=_IMAGE_DOC)


class SearchEmbeddingResponse(BaseModel):
    id: str
    object: str = "search_embedding"
    created: int
    model: str
    vector: list[float]                       # 128-d, L2-normalised; backend searches Milvus itself
    dim: int = 128
    metric: str = "COSINE"
    normalized: bool = True


class RecoVideoFeatures(BaseModel):
    video_id: str
    category_id: str | None = None
    content_embedding_256: list[float] | None = Field(None, min_length=256, max_length=256)
    positive_count: int = Field(0, ge=0)      # positive interactions in the training window (popularity feature)


class RecoUserFeatures(BaseModel):
    user_id: str
    preferred_category_ids: list[str] = Field(default_factory=list)
    positive_video_ids: list[str] = Field(default_factory=list, description="mỗi id phải có trong `videos` của cùng request")


class RecoEmbeddingRequest(BaseModel):
    model: str = "primitive-two-tower-recommender"
    videos: list[RecoVideoFeatures] = Field(default_factory=list, max_length=1000)
    users: list[RecoUserFeatures] = Field(default_factory=list, max_length=1000)


class VideoVector(BaseModel):
    video_id: str
    vector: list[float]


class UserVector(BaseModel):
    user_id: str
    vector: list[float]


class RecoEmbeddingResponse(BaseModel):
    id: str
    object: str = "recommendation_embeddings"
    created: int
    model: str
    feature_version: str = "ttv2-features-v1"
    dim: int = 128
    metric: str = "IP"                        # vectors L2-normalised → IP = cosine; score 0–1 = (IP + 1) / 2
    normalized: bool = True
    videos: list[VideoVector]
    users: list[UserVector]
