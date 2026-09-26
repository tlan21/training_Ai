"""Dataset loaders 6 model — khớp dataset_spec §3."""

from .asr_dataset import ASRDataset, CharVocab, collate_ctc
from .highlight_dataset import HighlightWindowDataset, load_highlight_labels, masked_bce_loss
from .movielens_dataset import (BPRTripleDataset, build_features, leave_last_k_split,
                                 load_movielens_ratings, time_split)
from .siamese_dataset import SiamesePairDataset
from .summary_dataset import SummaryPairDataset, normalize_to_asr
from .text_dataset import InMemoryTokenDataset, TextChunkDataset
from .vit_dataset import ViTKeyframeDataset

__all__ = [
    "ASRDataset", "CharVocab", "collate_ctc",
    "HighlightWindowDataset", "load_highlight_labels", "masked_bce_loss",
    "BPRTripleDataset", "build_features", "leave_last_k_split", "load_movielens_ratings", "time_split",
    "SiamesePairDataset",
    "SummaryPairDataset", "normalize_to_asr",
    "InMemoryTokenDataset", "TextChunkDataset",
    "ViTKeyframeDataset",
]
