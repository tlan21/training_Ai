"""Khoá bất biến của ablation T1.5e (evaluation_plan §2.1): chỉ-visual / chỉ-audio / fusion.

Ablation này là một khẳng định NHÂN QUẢ ("đa phương thức có đóng góp"), nên nó chỉ có giá trị khi
từng biến thể thật sự dùng đúng luồng của nó. Cả hai chiều đều phải kiểm:

  - biến thể đơn phương thức KHÔNG được nhìn thấy luồng kia — nếu lỡ nhìn thấy, bảng ablation so
    fusion với chính fusion và mọi kết luận rút ra đều sai;
  - fusion PHẢI thật sự nhìn thấy cả hai — cross-attn nối lỏng là no-op im lặng, đúng loại lỗi đã
    cắn hai lần trong dự án này (`cfg.dropout` không truyền xuống `TransformerBlock`, `SpecAugment`
    thoát sớm vì `self.training` False trong `Dataset`). Cả hai đều chạy trót lọt, không báo gì, và
    làm mọi thí nghiệm điều chỉnh chúng trở thành vô nghĩa.
"""

import pytest
import torch

from ai_core.config import ModelConfig
from ai_core.models.highlight_fusion import HighlightFusion

B, T, V, A = 2, 16, 256, 64


def _cfg(**kw):
    return ModelConfig(name="highlight_fusion", d_model=32, n_heads=4,
                       vision_dim=V, audio_dim=A, **kw)


def _model(**kw):
    torch.manual_seed(0)
    return HighlightFusion(_cfg(**kw)).eval()


def _inputs():
    torch.manual_seed(1)
    return torch.randn(B, T, V), torch.randn(B, T, A)


@torch.no_grad()
def test_visual_only_bo_qua_hoan_toan_audio():
    """Đổi audio bất kỳ cũng không được làm điểm đổi một chút nào."""
    model = _model(modality="visual")
    vis, aud = _inputs()
    out = model(vis, aud)
    assert torch.equal(out, model(vis, torch.randn_like(aud)))
    assert torch.equal(out, model(vis, torch.zeros_like(aud)))


@torch.no_grad()
def test_audio_only_bo_qua_hoan_toan_visual():
    model = _model(modality="audio")
    vis, aud = _inputs()
    out = model(vis, aud)
    assert torch.equal(out, model(torch.randn_like(vis), aud))
    assert torch.equal(out, model(torch.zeros_like(vis), aud))


@torch.no_grad()
def test_fusion_thuc_su_dung_ca_hai_luong():
    """Nửa còn lại của bất biến: fusion phải PHẢN ỨNG với thay đổi ở CẢ HAI luồng.

    Không có test này thì một cross-attn nối lỏng vẫn cho ablation "đạt": fusion trông như thắng
    chỉ-visual, nhưng thực chất nó cũng chỉ là chỉ-visual với nhiều tham số hơn.
    """
    model = _model(modality="fusion")
    vis, aud = _inputs()
    out = model(vis, aud)
    assert not torch.allclose(out, model(vis, torch.randn_like(aud)), atol=1e-6), \
        "đổi audio không làm điểm đổi → cross-attn audio→visual không được nối"
    assert not torch.allclose(out, model(torch.randn_like(vis), aud), atol=1e-6), \
        "đổi visual không làm điểm đổi → cross-attn visual→audio không được nối"


def test_khong_dung_module_cua_nhanh_khong_dung():
    """Tham số của nhánh chết phải bằng 0, không phải "có nhưng không train".

    Bảng ablation có cột số tham số. Nhánh chết vẫn nằm trong `state_dict` sẽ báo 5,4M cho biến thể
    chỉ-visual, khiến người đọc tưởng dung lượng đã khớp fusion trong khi thực tế không.
    """
    vis_only = _model(modality="visual")
    assert vis_only.aud_in is None and vis_only.aud_self is None
    assert vis_only.vis_cross is None and vis_only.aud_cross is None
    assert not any(k.startswith(("aud_", "vis_cross", "aud_cross"))
                   for k in vis_only.state_dict())

    aud_only = _model(modality="audio")
    assert aud_only.vis_in is None and aud_only.vis_self is None
    assert not any(k.startswith(("vis_", "aud_cross")) for k in aud_only.state_dict())


def test_n_self_dung_de_khop_dung_luong_voi_fusion():
    """Đối chứng khớp dung lượng phải thật sự khớp, không chỉ trên giấy.

    Fusion = 2+2 self + 2 cross. Cross-attn có thêm 1 RMSNorm + 1 MultiHeadAttention so với self,
    nên "6 block" của nhánh đơn không tự động bằng số tham số của fusion — phải đo.
    """
    n = lambda m: sum(p.numel() for p in m.parameters())
    fusion = n(_model(modality="fusion"))
    spec = n(_model(modality="visual"))
    matched = n(_model(modality="visual", n_self=6))

    assert spec < fusion / 2, "chỉ-visual theo spec phải nhỏ hơn hẳn fusion (nếu không, ablation " \
                              "không bị nhiễu dung lượng và đối chứng là dư)"
    assert matched > spec
    # Trong 25% là đủ để kết luận không phải chênh lệch dung lượng gây ra khác biệt F1.
    assert abs(matched - fusion) / fusion < 0.25, \
        f"n_self=6 ra {matched} tham số so với fusion {fusion} — chưa khớp đủ để làm đối chứng"


def test_modality_sai_bao_loi_ngay():
    """Sai chính tả modality phải nổ lúc dựng model, không âm thầm rơi về fusion.

    Rơi về fusion im lặng nghĩa là một dòng trong bảng ablation ghi "visual" nhưng số là của fusion.
    """
    with pytest.raises(ValueError, match="modality"):
        HighlightFusion(_cfg(modality="vision"))     # dễ gõ nhầm 'visual'


# ---- chế độ chấm `eval_highlight --ablation` -------------------------------------------------

def _fake_run(root, name, seed, **kw):
    """Ghi 1 checkpoint như Trainer sinh ra, để chấm được mà không cần GPU."""
    from ai_core.training.checkpoint import save_checkpoint

    cfg = ModelConfig(name="highlight_fusion", d_model=32, n_heads=4,
                      vision_dim=V, audio_dim=A, window_seconds=8, **kw)
    torch.manual_seed(seed)
    save_checkpoint(str(root / f"ckpt_abl_{name}_s{seed}" / "highlight_fusion" / "best.pt"),
                    HighlightFusion(cfg), cfg, {"seed": seed, "step": 100, "f1": 0.1})


def _features(n=24):
    torch.manual_seed(3)
    return {"val": [{"name": "g00h1", "vision": torch.randn(n, V), "audio": torch.randn(n, A),
                     "labels": torch.randint(0, 2, (n,))}]}


def test_ablation_dung_lai_dung_kien_truc_tung_bien_the(tmp_path):
    """Mỗi biến thể phải được dựng lại theo `config` TRONG checkpoint của nó.

    Nếu chấm bằng một `ModelConfig` mặc định dùng chung thì `load_state_dict` của biến thể chỉ-visual
    sẽ đòi thêm khoá `aud_*` và nổ — nhưng nếu ai đó "sửa" bằng `strict=False` thì nó im lặng chấm
    một model nửa random. Test này khoá đường đúng: đọc config từ checkpoint.
    """
    import json

    from ai_core.scripts.eval_highlight import ablation

    for name, kw in [("fusion", {}), ("visual", dict(modality="visual")),
                     ("audio", dict(modality="audio")),
                     ("visual_deep", dict(modality="visual", n_self=6))]:
        for seed in (1337, 1338):
            _fake_run(tmp_path, name, seed, **kw)
    torch.save(_features(), tmp_path / "features.pt")

    out = tmp_path / "abl.json"
    ablation(type("A", (), {
        "features": str(tmp_path / "features.pt"), "ablation": str(tmp_path), "out": str(out),
        "ablation_variants": ["fusion", "visual", "audio", "visual_deep", "audio_deep"]})())

    got = json.loads(out.read_text(encoding="utf-8"))
    assert set(got["variants"]) == {"fusion", "visual", "audio", "visual_deep"}, \
        "audio_deep không có checkpoint → phải bị bỏ qua, không được dựng số từ hư không"
    assert got["variants"]["visual"]["modality"] == "visual"
    assert got["variants"]["visual_deep"]["n_self"] == 6
    assert len(got["variants"]["fusion"]["seeds"]) == 2
    # Cột dung lượng phải phản ánh kiến trúc thật, không phải cùng một số cho mọi dòng.
    n = {k: v["n_params"] for k, v in got["variants"].items()}
    assert n["visual"] < n["fusion"] and n["visual"] < n["visual_deep"]
    assert set(got["gaps_vs_fusion"]) == {"visual", "audio", "visual_deep"}


def test_che_do_dod_bao_thieu_doi_so_thay_vi_no_giua_duong(tmp_path):
    """`--audio`/`--frames` đã bỏ required=True cho --ablation, nên chế độ DoD phải tự kiểm.

    Không kiểm thì `os.path.join(None, ...)` nổ TypeError sau khi đã nạp xong features — thông báo
    không liên quan gì tới nguyên nhân thật là thiếu đối số.
    """
    import sys

    from ai_core.scripts.eval_highlight import main

    argv = ["eval_highlight", "--features", str(tmp_path / "f.pt"), "--out", str(tmp_path / "o.json")]
    old, sys.argv = sys.argv, argv
    try:
        with pytest.raises(SystemExit, match="checkpoints"):
            main()
    finally:
        sys.argv = old
