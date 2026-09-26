"""Khoá 4 chỗ dễ sai âm thầm trong bước chấm DoD T1.5.

Cả bốn đều thuộc loại "chạy trót lọt, ra số sai": bản frame-diff chạy trôi lệch công thức so với
baseline đã test, model bỏ sót giây ở cửa sổ cuối, sweep τ không thật sự chọn ngưỡng, và giây
IGNORE lọt vào phép chọn τ.
"""

import torch

from ai_core.baselines import frame_diff_score
from ai_core.config import ModelConfig
from ai_core.models.highlight_fusion import HighlightFusion
from ai_core.scripts.eval_highlight import (_fit, frame_diff_scores, model_scores, model_scores_overlap,
                                            smooth, sweep_k_tau, sweep_tau)


def _write_png_sequence(tmp_path, frames):
    from PIL import Image

    d = tmp_path / "g00h1"
    d.mkdir()
    for sec, f in enumerate(frames):
        Image.fromarray((f.permute(1, 2, 0) * 255).byte().numpy()).save(d / f"g00h1_s{sec:05d}.png")
    return str(d)


def test_streaming_frame_diff_matches_batch_version(tmp_path):
    """Bản chạy trôi phải ra ĐÚNG số của `frame_diff_score`; lệch thì baseline trong báo cáo không
    còn là baseline đã được test ở test_baselines.py."""
    torch.manual_seed(0)
    frames = (torch.rand(6, 3, 8, 6) * 255).byte().float() / 255      # qua byte: khớp lượng tử PNG
    got = frame_diff_scores(_write_png_sequence(tmp_path, frames), 6)
    assert torch.allclose(got, frame_diff_score(frames), atol=1e-4)


def test_model_scores_cover_every_second_and_ignore_padding():
    """n không chia hết cho window: phải ra đúng n điểm, và điểm các giây thật không đổi vì phần
    đệm 0 ở cửa sổ cuối."""
    cfg = ModelConfig(name="highlight_fusion", d_model=32, n_heads=4,
                      vision_dim=16, audio_dim=8, window_seconds=4)
    model = HighlightFusion(cfg).eval()
    n = 10                                                            # 2 cửa sổ đủ + 1 cửa sổ 2 giây
    sample = {"vision": torch.randn(n, 16), "audio": torch.randn(n, 8)}
    got = model_scores(model, sample, cfg.window_seconds)
    assert got.shape == (n,)

    with torch.no_grad():                                             # 4 giây đầu = forward trực tiếp
        direct = model(sample["vision"][:4].unsqueeze(0), sample["audio"][:4].unsqueeze(0))[0]
    assert torch.allclose(got[:4], direct, atol=1e-6)


def test_sweep_tau_beats_the_hardcoded_half():
    """Dựng trường hợp 0.5 KHÔNG phải ngưỡng tốt nhất: ở τ=0.5 giây thứ tư thành FP (F1 0.857).
    Sweep trả về 0.5 nghĩa là nó không sweep."""
    scores = torch.tensor([0.9, 0.7, 0.6, 0.55, 0.2, 0.1])
    labels = torch.tensor([1, 1, 1, 0, 0, 0])
    tau, f1 = sweep_tau(scores, labels)
    assert 0.55 <= tau < 0.6 and f1 == 1.0


def test_sweep_tau_ignores_masked_seconds():
    """Giây IGNORE không được tính vào F1 lúc chọn τ, nếu không τ bị kéo lệch bởi giây không nhãn."""
    scores = torch.tensor([0.9, 0.1, 0.9, 0.9])
    labels = torch.tensor([1, 0, -1, -1])
    assert sweep_tau(scores, labels)[1] == 1.0


def test_fit_trims_and_pads():
    """Độ dài WAV/số PNG lệch vài giây so với nhãn — cắt hoặc đệm 0, luôn ra đúng n."""
    assert _fit(torch.ones(5), 3).tolist() == [1, 1, 1]
    assert _fit(torch.ones(2), 4).tolist() == [1, 1, 0, 0]


def test_overlap_scores_average_every_covering_window():
    """Giây 0 chỉ nằm trong cửa sổ đầu, giây cuối chỉ nằm trong cửa sổ áp sát cuối hiệp; giây giữa
    là trung bình ĐÚNG các cửa sổ phủ nó — sai chỉ số là lệch điểm mà vẫn ra số trông hợp lý."""
    torch.manual_seed(0)
    cfg = ModelConfig(name="highlight_fusion", d_model=32, n_heads=4,
                      vision_dim=16, audio_dim=8, window_seconds=4)
    model = HighlightFusion(cfg).eval()
    n = 9                                                             # cửa sổ 0,2,4 + cửa sổ cuối 5
    sample = {"vision": torch.randn(n, 16), "audio": torch.randn(n, 8)}
    got = model_scores_overlap(model, sample, 4, 2)
    with torch.no_grad():
        f = {s: model(sample["vision"][s:s + 4][None], sample["audio"][s:s + 4][None])[0] for s in (0, 2, 4, 5)}
    assert got.shape == (n,)
    assert torch.allclose(got[0], f[0][0], atol=1e-6)
    assert torch.allclose(got[8], f[5][3], atol=1e-6)
    assert torch.allclose(got[5], (f[2][3] + f[4][1] + f[5][0]) / 3, atol=1e-6)


def test_smooth_keeps_length_and_constants():
    x = torch.rand(10)
    assert torch.equal(smooth(x, 1), x)
    assert smooth(x, 5).shape == (10,)
    assert torch.allclose(smooth(torch.full((10,), 0.3), 9), torch.full((10,), 0.3))


def test_sweep_k_tau_picks_smoothing_on_noisy_block():
    """Đoạn dương liền khối + nhiễu xen kẽ: ngưỡng từng giây cắt vụn, làm mượt phải thắng. Với
    ks=[1] phải trả đúng số của sweep_tau cũ — mặc định CLI tái lập các vòng trước."""
    labels = torch.tensor([0] * 20 + [1] * 20 + [0] * 20)
    noise = torch.tensor([0.35, -0.35] * 30)
    scores = (labels * 0.4 + 0.3 + noise).clamp(0, 1)
    k, _, f1 = sweep_k_tau([scores], labels, [1, 3, 5])
    assert k > 1 and f1 > sweep_tau(scores, labels)[1]
    assert sweep_k_tau([scores], labels, [1])[1:] == sweep_tau(scores, labels)
