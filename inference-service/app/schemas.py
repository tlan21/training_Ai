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


# ---------------- /v1/search/completions (Siamese ViT) ----------------

class SearchRequest(BaseModel):
    model: str = "primitive-siamese-vit"
    image: str = Field(..., description="data URI base64 hoặc path")
    top_k: int = Field(5, ge=1, le=100)
    threshold: float = Field(0.75, ge=0, le=1)


class SearchResult(BaseModel):
    video_id: str
    timestamp: float
    similarity_score: float           # 0–1 (cosine)
    thumbnail_url: str


class SearchResponse(BaseModel):
    id: str
    object: str = "search_completion"
    created: int
    model: str
    results: list[SearchResult]
    query_metadata: dict


# ---------------- /v1/highlight/completions (Fusion) ----------------

class HighlightFeatures(BaseModel):
    vision_embeddings: list[list[float]]
    audio_spectrogram_features: list[list[float]]


class HighlightRequest(BaseModel):
    model: str = "primitive-seq2seq-highlighter"
    video_id: str
    features: HighlightFeatures


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


# ---------------- /v1/asr/completions (ASR CTC) ----------------

class ASRRequest(BaseModel):
    model: str = "primitive-asr-transformer"
    audio_url: str
    language: str = "vi"


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


# ---------------- /v1/recommendation/completions (Two-Tower) ----------------

class RecommendationRequest(BaseModel):
    model: str = "primitive-two-tower-recommender"
    user_id: str
    limit: int = 10
    context: dict = Field(default_factory=dict)


class Recommendation(BaseModel):
    video_id: str
    score: float                      # 0–1 (inner product)
    title: str
    thumbnail_url: str


class RecommendationResponse(BaseModel):
    id: str
    object: str = "recommendation_completion"
    created: int
    model: str
    recommendations: list[Recommendation]


# ---------------- /v1/vision/completions (ViT — nội bộ pipeline) ----------------

class VisionRequest(BaseModel):
    model: str = "primitive-vit-classifier"
    keyframes: list[str] = Field(..., description="paths hoặc base64 keyframe")


class VisionResponse(BaseModel):
    id: str
    object: str = "vision_completion"
    created: int
    model: str
    category_suggestion: str
    embeddings_256: list[list[float]]


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
