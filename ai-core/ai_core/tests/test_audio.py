"""Kiểm tra mel scale + log-mel shape + features 64-d — plan 01 §5."""

import torch

from ai_core.audio import (
    audio_features_per_second,
    hz_to_mel,
    log_mel_spectrogram,
    mel_filterbank,
    mel_to_hz,
)


def test_mel_scale_formula():
    # mel(0)=0; roundtrip hz→mel→hz
    assert abs(hz_to_mel(0.0).item()) < 1e-6
    for f in [100.0, 1000.0, 4000.0]:
        assert abs(mel_to_hz(hz_to_mel(f)).item() - f) < 1e-2


def test_mel_filterbank_shape():
    fb = mel_filterbank(n_mels=80, n_fft=400, sr=16000)
    assert fb.shape == (80, 201)
    assert (fb >= 0).all()


def test_log_mel_shape():
    sig = torch.randn(16000)                              # 1s @ 16kHz
    lm = log_mel_spectrogram(sig, n_mels=80, n_fft=400, hop=160)
    assert lm.shape[0] == 80
    assert lm.shape[1] > 90                               # ~100 frame/giây


def test_audio_features_dim():
    sig = torch.randn(16000 * 3)                          # 3 giây
    feats = audio_features_per_second(sig)
    assert feats.shape == (3, 64)


def test_khong_co_chieu_nao_la_hang_so():
    """Mọi chiều trong 64 phải mang thông tin — không chiều nào bất biến theo dữ liệu.

    Bản trước dùng 36 chiều thật rồi pad 28 chiều toàn 0, nên `audio_dim=64` của model_spec §2 mô tả
    một thứ không tồn tại: 44% đầu vào nhánh audio là hằng số. `test_audio_features_dim` vẫn pass vì
    nó chỉ chấm SHAPE — shape đúng, nội dung rỗng, không có gì báo.
    """
    torch.manual_seed(0)
    feats = torch.cat([audio_features_per_second(torch.randn(16000 * 4) * a)
                       for a in (0.1, 1.0, 5.0)])
    const = (feats.std(dim=0) < 1e-8).nonzero().flatten().tolist()
    assert not const, f"chiều bất biến (khả năng là đệm): {const}"


def test_onset_bat_duoc_transient_ma_mean_bo_qua():
    """Chiều `onset` phải phân biệt được cú tăng VỌT với cú tăng CHẬM cùng biên độ cuối.

    Đây là lý do tồn tại của cả bản nâng: tiếng khán giả reo lúc dứt điểm là transient sắc. Nếu chỉ
    có `mean` thì hai tín hiệu dưới đây cho gần như cùng một vector, và nhánh audio không có cách nào
    thấy khác biệt — trong khi T1.5e đo được audio là luồng mang tín hiệu chính.
    """
    sr, n = 16000, 16000 * 2
    t = torch.arange(n, dtype=torch.float32) / sr
    tone = torch.sin(2 * torch.pi * 440 * t)
    burst = tone * torch.where(t > 1.0, 1.0, 0.02)        # nhảy bậc tại mốc 1 giây
    ramp = tone * (0.02 + 0.98 * (t / t[-1]))             # tăng tuyến tính, cùng biên độ cuối

    onset_b = audio_features_per_second(burst, sr)[:, 44:].max().item()
    onset_r = audio_features_per_second(ramp, sr)[:, 44:].max().item()
    assert onset_b > 2 * onset_r, \
        f"onset không phân biệt được bậc nhảy ({onset_b:.3f}) với dốc chậm ({onset_r:.3f})"


# ---------------- SpecAugment phải THẬT SỰ được áp trong ASRDataset (T1.4c) ----------------

def _asr_dataset(tmp_path, augment):
    import soundfile as sf

    from ai_core.data import ManifestItem, save_manifest
    from ai_core.training.datasets import ASRDataset, CharVocab

    tmp_path.mkdir(parents=True, exist_ok=True)
    wav = tmp_path / "utt.wav"
    sf.write(wav, torch.randn(16000).numpy(), 16000)      # 1 giây nhiễu
    man = tmp_path / "asr.json"
    save_manifest(man, [ManifestItem(path=str(wav), label="vi", split="train", group="SPK01",
                                     extra={"transcript": "ABC"})], meta={"sr": 16000})
    return ASRDataset(str(man), "train", CharVocab(list("ABC")), augment=augment)


def test_spec_augment_actually_masks_when_enabled(tmp_path):
    """`SpecAugment.forward` thoát sớm nếu `self.training` False, mà Dataset không phải nn.Module
    nên không ai gọi .train() cho nó — khởi tạo rồi dùng thẳng là no-op âm thầm. Khoá lại: bật
    augment thì phải có ô bị che về 0."""
    torch.manual_seed(0)
    mel = _asr_dataset(tmp_path, augment=True)[0][0]
    assert (mel == 0).any(), "không ô nào bị che → SpecAugment không chạy"


def test_spec_augment_off_by_default(tmp_path):
    """Val/test không được augment, nếu không số đo dao động theo may rủi từng lần chạy."""
    ds = _asr_dataset(tmp_path, augment=False)
    assert ds.spec_augment is None
    assert torch.equal(ds[0][0], ds[0][0])                # tất định
