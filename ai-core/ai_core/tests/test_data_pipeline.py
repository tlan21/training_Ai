"""Test logic thuần T1.2: shot boundary, weak-label, collate, dataset, metrics — không cần dữ liệu thật."""

import torch

from ai_core.data.manifest import ManifestItem, load_manifest, save_manifest, split_by_group
from ai_core.data.weak_label import IGNORE, build_weak_labels, mel_cross_correlation
from ai_core.vision.shot_boundary import (
    color_histogram,
    detect_shot_boundaries,
    is_black_frame,
)


# ---------- manifest ----------

def test_split_by_group_deterministic():
    groups = [f"vid{i}" for i in range(20)]
    s1 = split_by_group(groups, seed=1337)
    s2 = split_by_group(groups, seed=1337)
    assert s1 == s2
    counts = {v: list(s1.values()).count(v) for v in ("train", "val", "test")}
    assert counts["train"] == 16 and counts["val"] == 2 and counts["test"] == 2


def test_manifest_roundtrip(tmp_path):
    items = [ManifestItem(path="a.png", label="foot", split="train", group="v1"),
             ManifestItem(path="b.png", label="game", split="test", group="v2")]
    p = str(tmp_path / "m.json")
    save_manifest(p, items, meta={"seed": 1})
    got = load_manifest(p, split="train")
    assert len(got) == 1 and got[0].label == "foot"


# ---------- shot boundary ----------

def test_black_frame_detection():
    black = torch.zeros(3, 32, 32)
    normal = torch.rand(3, 32, 32)
    assert is_black_frame(black)
    assert not is_black_frame(normal)


def test_shot_boundaries():
    # 3 frame đỏ rồi 3 frame xanh → boundary tại index 3
    red = torch.zeros(3, 16, 16); red[0] = 1.0
    blue = torch.zeros(3, 16, 16); blue[2] = 1.0
    frames = torch.stack([red, red, red, blue, blue, blue])
    b = detect_shot_boundaries(frames, threshold=0.5)
    assert 3 in b


def test_color_histogram_normalized():
    h = color_histogram(torch.rand(3, 16, 16), bins=8)
    assert abs(h.sum().item() - 1.0) < 1e-4


# ---------- weak label ----------

def test_cross_correlation_finds_offset():
    torch.manual_seed(0)
    full = torch.randn(80, 200)
    seg = full[:, 50:70].clone()                     # đoạn khớp tại offset 50
    off, score = mel_cross_correlation(seg, full)
    assert off == 50 and score > 0.99


def test_cross_correlation_matches_bruteforce():
    # FFT cross-correlation phải khớp cosine trượt brute-force.
    torch.manual_seed(3)
    full = torch.randn(80, 120)
    seg = full[:, 33:53].clone()
    off, score = mel_cross_correlation(seg, full)
    # brute-force cosine
    import torch.nn.functional as F
    best_off, best = 0, -1.0
    for o in range(full.shape[1] - seg.shape[1] + 1):
        c = F.cosine_similarity(seg.flatten(0, 1)[None], full[:, o:o + seg.shape[1]].flatten(0, 1)[None]).item()
        if c > best:
            best, best_off = c, o
    assert off == best_off == 33
    assert abs(score - (best + 1) / 2) < 1e-4


def test_build_weak_labels_states():
    torch.manual_seed(0)
    full = torch.randn(80, 200)                       # 200 frame
    seg = full[:, 40:60].clone()
    # frames_per_second=10 → 200 frame = 20s; đoạn tại frame 40 = giây 4, dài 2s
    labels, coverage = build_weak_labels(full, [seg], frames_per_second=10, n_seconds=20,
                                         match_threshold=0.6, dilation_sec=2)
    assert coverage == 1.0
    assert (labels == 1).any()
    assert (labels == IGNORE).any()                  # dilation quanh biên
    assert (labels == 0).any()


# ---------- collate CTC ----------

def test_vit_class_map_consistent_across_splits(tmp_path):
    # Nhãn→idx phải giống nhau giữa train và val dù val thiếu 1 lớp (chống lệch index).
    from ai_core.training.datasets import ViTKeyframeDataset
    items = [
        ManifestItem(path="a.png", label="game", split="train", group="v1"),
        ManifestItem(path="b.png", label="nhac", split="train", group="v2"),
        ManifestItem(path="c.png", label="tin", split="train", group="v3"),
        ManifestItem(path="d.png", label="game", split="val", group="v4"),  # val chỉ có 'game'
    ]
    p = str(tmp_path / "vit.json")
    save_manifest(p, items)
    tr = ViTKeyframeDataset(p, "train")
    va = ViTKeyframeDataset(p, "val")
    assert tr.class_to_idx == va.class_to_idx
    assert va.class_to_idx["game"] == tr.class_to_idx["game"]


def test_siamese_no_group_same_frame(tmp_path):
    # Item thiếu group → partner = chính nó (same-frame), KHÔNG lấy cross-video.
    from ai_core.training.datasets.siamese_dataset import SiamesePairDataset
    items = [ManifestItem(path=f"{i}.png", label="x", split="train", group=None) for i in range(5)]
    p = str(tmp_path / "s.json")
    save_manifest(p, items)
    ds = SiamesePairDataset(p, "train")
    assert all(ds._partner_idx(i) == i for i in range(len(ds)))


def test_siamese_same_shot_partner(tmp_path):
    # Cùng group, sec cách 1–10 → partner khác idx (cặp dương cùng shot).
    from ai_core.training.datasets.siamese_dataset import SiamesePairDataset
    items = [ManifestItem(path=f"{s}.png", label="x", split="train", group="v1", extra={"sec": s})
             for s in range(6)]
    p = str(tmp_path / "s2.json")
    save_manifest(p, items)
    ds = SiamesePairDataset(p, "train")
    # frame giây 0 phải ghép được frame trong giây 1..5 (gap ≤10)
    assert ds._partner_idx(0) != 0


def test_collate_ctc_shapes():
    from ai_core.training.datasets import collate_ctc
    batch = [(torch.randn(80, 100), torch.tensor([1, 2, 3])),
             (torch.randn(80, 60), torch.tensor([4, 5]))]
    mel, mel_len, tgt, tgt_len = collate_ctc(batch)
    assert mel.shape == (2, 80, 100)
    assert mel_len.tolist() == [100, 60]
    assert tgt.shape == (2, 3) and tgt_len.tolist() == [3, 2]


# ---------- text dataset + minigpt loss wiring ----------

def test_text_dataset_and_minigpt_step():
    from ai_core import build_model
    from ai_core.config import ModelConfig
    from ai_core.training.datasets import InMemoryTokenDataset
    from ai_core.training.loss_fns import minigpt_loss

    ids = torch.randint(0, 50, (200,))
    ds = InMemoryTokenDataset(ids, context_len=16)
    x, y = ds[0]
    assert x.shape == (16,) and y.shape == (16,)

    model = build_model("minigpt", ModelConfig(name="minigpt", d_model=32, n_layers=2,
                                               n_heads=4, vocab_size=50, context_len=64))
    loss = minigpt_loss(model, (x.unsqueeze(0), y.unsqueeze(0)))
    assert loss.item() > 0


# ---------- summary ASR normalization ----------

def test_normalize_to_asr_removes_punct():
    from ai_core.training.datasets import normalize_to_asr
    out = normalize_to_asr("Xin chào, Việt Nam!", cer=0.0, seed=0)
    assert "," not in out and "!" not in out
    assert out == out.lower()


# ---------- metrics ----------

def test_wer_cer():
    from ai_core.scripts.evaluate import cer, wer
    assert wer("a b c", "a b c") == 0.0
    assert abs(wer("a b c d", "a b x d") - 0.25) < 1e-9
    assert cer("abcd", "abxd") == 0.25


def test_ndcg_and_recall():
    from ai_core.scripts.evaluate import ndcg_at_k, recall_at_k
    ranked = [[1, 2, 3, 4]]
    rel = [{3}]
    assert recall_at_k(ranked, rel, k=3) == 1.0
    assert recall_at_k(ranked, rel, k=2) == 0.0
    assert 0 < ndcg_at_k(ranked, rel, k=4) < 1.0


def test_rouge_l():
    from ai_core.scripts.evaluate import rouge_l
    assert rouge_l("a b c", "a b c") == 1.0
    assert 0 < rouge_l("a b c d", "a b x d") < 1.0


def test_eval_recommender_scores_both_on_same_users():
    """Bug đã gặp: model và popularity eval trên tập user khác nhau → so sánh vô nghĩa.

    Model giả xếp hạng item theo ID ngược, popularity xếp theo tần suất train. Cả hai phải
    được chấm trên cùng user, và popularity phải được TÍNH, không phải hằng số.
    """
    import torch
    from ai_core.scripts.evaluate import eval_recommender

    n_items = 6
    video_features = {i: torch.eye(n_items)[i - 1] for i in range(1, n_items + 1)}
    user_features = {u: torch.ones(3) * u for u in (1, 2, 3)}

    # item 1 phổ biến nhất trong train; test positive của mỗi user là item 6.
    train_rows = [(1, 1, 0), (2, 1, 1), (3, 1, 2), (1, 2, 3), (2, 2, 4)]
    test_rows = [(u, 6, 10) for u in (1, 2, 3)]

    class ReverseIdModel:
        """user_embed/video_embed sao cho score cao ⇔ item ID lớn."""

        def eval(self): pass
        def user_embed(self, x): return torch.ones(x.shape[0], n_items)
        def video_embed(self, x): return x * torch.arange(1, n_items + 1).float()

    m = eval_recommender(
        ReverseIdModel(), user_features, video_features, train_rows, test_rows, k=3, n_users=10
    )

    assert m["n_users"] == 3                    # cả 3 user, không ai bị rơi
    assert m["model_recall"] == 1.0             # item 6 luôn vào top-3 của model
    assert m["pop_recall"] == 0.0               # popularity không bao giờ chạm item 6
    assert m["pop_ndcg"] == 0.0                 # baseline được tính, không hardcode
    assert m["model_ndcg"] > m["pop_ndcg"]


# ---------- negative sampling + logQ correction ----------

def _bpr_fixture(neg_alpha: float, seed: int = 7):
    from ai_core.training.datasets import BPRTripleDataset
    items = list(range(1, 11))
    video_features = {i: torch.zeros(2) for i in items}
    user_features = {u: torch.zeros(3) for u in (1, 2, 3)}
    # item 1 chiếm 20/30 lượt tương tác → phổ biến áp đảo.
    # user 3 chỉ thích item 5 → 9 negative hợp lệ, đủ chỗ để thấy phân phối lệch.
    ratings = ([(1, 1, t) for t in range(20)]
               + [(2, i, 100 + i) for i in items[1:]]
               + [(3, 5, 200)])
    return BPRTripleDataset(ratings, user_features, video_features, len(items),
                            seed=seed, neg_alpha=neg_alpha)


def test_neg_alpha_zero_is_uniform_and_matches_old_behaviour():
    ds = _bpr_fixture(neg_alpha=0.0)
    assert len(set(ds.log_q.values())) == 1                      # mọi item cùng log q
    assert abs(ds.log_q[1] - torch.tensor(1 / 10).log().item()) < 1e-6


def test_neg_alpha_skews_sampling_toward_popular_items():
    """Uniform negative gần như không rơi vào vùng popular — đó là lý do model thua popularity."""
    uniform = _bpr_fixture(neg_alpha=0.0)
    skewed = _bpr_fixture(neg_alpha=1.0)

    assert skewed.log_q[1] > skewed.log_q[2]                     # item phổ biến q cao hơn
    assert abs(uniform.log_q[1] - uniform.log_q[2]) < 1e-9       # uniform thì không

    # user 3 chỉ loại item 5, nên item 1 luôn là negative hợp lệ. Với uniform, item 1 được
    # chọn ~1/9 lượt; với alpha=1 (item 1 chiếm 21/30 trọng số) thì phải áp đảo.
    def neg_rate(ds):
        ds.rng.seed(0)
        hits = sum(ds._sample_negative(3) == 1 for _ in range(900))
        return hits / 900

    rate_uniform, rate_skewed = neg_rate(uniform), neg_rate(skewed)
    assert 0.05 < rate_uniform < 0.20            # xấp xỉ 1/9
    assert rate_skewed > 3 * rate_uniform


def test_logq_correction_is_noop_under_uniform_sampling():
    """log q trừ ở CẢ pos và neg nên hằng số triệt tiêu — nếu chỉ trừ ở neg, loss sẽ lệch."""
    from ai_core.config import ModelConfig
    from ai_core.models import TwoTower

    torch.manual_seed(0)
    model = TwoTower(ModelConfig(name="two_tower", proj_dim=8), user_dim=4, video_dim=4)
    u, pos, neg = torch.randn(6, 4), torch.randn(6, 4), torch.randn(6, 4)
    log_q = torch.full((6,), -2.3)                               # uniform: pos và neg cùng q

    plain = model(u, pos, neg)
    corrected = model(u, pos, neg, log_q, log_q)
    assert torch.allclose(plain, corrected, atol=1e-6)


def test_logq_correction_penalises_popular_negatives():
    """Negative phổ biến (q cao) bị trừ nhiều hơn → margin nhỏ hơn → loss lớn hơn."""
    from ai_core.config import ModelConfig
    from ai_core.models import TwoTower

    torch.manual_seed(0)
    model = TwoTower(ModelConfig(name="two_tower", proj_dim=8), user_dim=4, video_dim=4)
    u, pos, neg = torch.randn(6, 4), torch.randn(6, 4), torch.randn(6, 4)
    log_q_pos = torch.full((6,), -5.0)                           # positive hiếm
    rare_neg, popular_neg = torch.full((6,), -5.0), torch.full((6,), -1.0)

    loss_rare = model(u, pos, neg, log_q_pos, rare_neg)
    loss_popular = model(u, pos, neg, log_q_pos, popular_neg)
    assert loss_popular < loss_rare      # -log_q_neg lớn hơn → s_neg thấp hơn → margin rộng hơn


def test_temperature_scales_logits():
    from ai_core.config import ModelConfig
    from ai_core.models import TwoTower

    torch.manual_seed(0)
    u, pos, neg = torch.randn(6, 4), torch.randn(6, 4), torch.randn(6, 4)
    cfg_hot = ModelConfig(name="two_tower", proj_dim=8, temperature=0.05)
    torch.manual_seed(0)
    hot = TwoTower(cfg_hot, user_dim=4, video_dim=4)
    torch.manual_seed(0)
    cold = TwoTower(ModelConfig(name="two_tower", proj_dim=8, temperature=1.0), user_dim=4, video_dim=4)

    assert hot.temperature == 0.05
    assert not torch.allclose(hot(u, pos, neg), cold(u, pos, neg))


def test_bpr_dataset_returns_six_tuple_with_log_q_and_item_id():
    ds = _bpr_fixture(neg_alpha=0.75)
    row = ds[0]
    assert len(row) == 6
    user, pos, neg, log_q_pos, log_q_neg, pos_id = row
    assert user.shape == (3,) and pos.shape == (2,) and neg.shape == (2,)
    assert log_q_pos.shape == () and log_q_neg.shape == ()
    assert log_q_pos.item() < 0 and log_q_neg.item() < 0          # log của xác suất
    assert pos_id.item() == ds.pos[0][1]                          # id item positive, để mask dup


# ---------- in-batch sampled softmax ----------

def _softmax_batch(item_ids, log_q, seed=0):
    """Batch 6 phần tử cho two_tower_softmax_loss; cùng id → cùng feature item."""
    torch.manual_seed(seed)
    ids = torch.tensor(item_ids, dtype=torch.long)
    pos = torch.eye(8)[ids % 8]
    user = torch.randn(len(item_ids), 4)
    return (user, pos, torch.randn(len(item_ids), 8),
            torch.tensor(log_q, dtype=torch.float32),
            torch.tensor(log_q, dtype=torch.float32), ids)


def _softmax_model(temperature=1.0):
    from ai_core.config import ModelConfig
    from ai_core.models import TwoTower
    torch.manual_seed(0)
    return TwoTower(ModelConfig(name="two_tower", proj_dim=8, temperature=temperature),
                    user_dim=4, video_dim=8)


def test_softmax_loss_masks_accidental_hits():
    """Cả batch cùng một item → mọi cột đều là positive thật, mask hết thì loss = 0.

    Không mask, softmax coi chúng là negative và loss ≈ log(B): gradient tự triệt tiêu đúng ở
    vùng item phổ biến — nơi ground truth tập trung.
    """
    from ai_core.training.loss_fns import two_tower_softmax_loss

    model = _softmax_model()
    same = two_tower_softmax_loss(model, _softmax_batch([3] * 4, [-2.0] * 4))
    assert same.item() < 1e-6

    distinct = two_tower_softmax_loss(model, _softmax_batch([1, 2, 3, 4], [-2.0] * 4))
    assert distinct.item() > 0.5                                  # có negative thật thì phải có loss


def test_softmax_loss_logq_applies_to_candidate_columns_only():
    """log q trừ theo CỘT candidate: đối thủ phổ biến bị hạ logit → loss thấp hơn.

    Trừ theo hàng (positive) thì thay đổi log_q của cột 1 sẽ không cho ra hướng này → test đổ.
    """
    from ai_core.training.loss_fns import two_tower_softmax_loss

    model = _softmax_model()
    rare_rival = two_tower_softmax_loss(model, _softmax_batch([1, 2], [-2.0, -8.0]))
    popular_rival = two_tower_softmax_loss(model, _softmax_batch([1, 2], [-2.0, -1.0]))
    assert popular_rival.item() < rare_rival.item()


def test_logq_correction_approximates_full_softmax_gradient():
    """Kiểm chứng SỐ HỌC mục đích của logQ correction, chạy qua CHÍNH `two_tower_softmax_loss`.

    In-batch sampled softmax là công cụ xấp xỉ softmax trên TOÀN catalog. Catalog nhỏ (40 item)
    nên tính được chuẩn vàng, rồi so gradient THAM SỐ tích luỹ qua nhiều batch với chuẩn vàng:
    có logQ → cosine 0.99; không có → 0.54.

    Đây là test duy nhất phân biệt được công thức đúng/sai. Đã kiểm bằng mutation:
      - trừ theo HÀNG thay vì cột → 0.54 (bị bắt). Hằng số theo hàng không đổi softmax trên cột
        nên sai trục là no-op IM LẶNG — không test nào khác thấy.
      - `+ log_q` thay vì `-` → −0.76 (bị bắt).
      - bỏ hẳn correction → 0.54 (bị bắt).
      - chỉ trừ off-diagonal → 0.9907, KHÔNG phân biệt được với 0.9910. Việc có trừ ở đường chéo
        hay không là vô hại; trục và dấu mới là thứ quyết định.
    Phải gọi hàm thật qua autograd: bản test tự tái tạo công thức sẽ pass kể cả khi implementation
    bị sửa sai.
    """
    from ai_core.config import ModelConfig
    from ai_core.models import TwoTower
    from ai_core.training.loss_fns import two_tower_softmax_loss

    N, U, D, B, R, temp = 40, 8, 8, 16, 150, 0.1
    counts = torch.tensor([max(1, int(200 / (i + 1))) for i in range(N)], dtype=torch.float32)
    q = counts / counts.sum()                       # popularity lệch mạnh giống MovieLens
    log_q = q.log()

    def fresh_model():
        torch.manual_seed(0)                        # cùng khởi tạo → gradient so được với nhau
        cfg = ModelConfig(name="two_tower", proj_dim=D, temperature=temp, user_dim=U, video_dim=N)
        return TwoTower(cfg, user_dim=U, video_dim=N)

    def flat_grad(m):
        return torch.cat([p.grad.reshape(-1) for p in m.parameters() if p.grad is not None])

    # Chuẩn vàng: full softmax trên cả N item, target ~ q.
    ref_model = fresh_model()
    ref_model.zero_grad()
    logits_full = (ref_model.user_embed(torch.eye(U))
                   @ ref_model.video_embed(torch.eye(N)).T) / ref_model.temperature
    (-(q.unsqueeze(0) * torch.log_softmax(logits_full, dim=1)).sum() / U).backward()
    ref = flat_grad(ref_model)
    ref = ref / ref.norm()

    gen = torch.Generator().manual_seed(1234)
    rows = torch.randint(0, U, (R, B), generator=gen)
    cols = torch.multinomial(q, R * B, replacement=True, generator=gen).view(R, B)

    def cosine_to_ref(corrected: bool) -> float:
        m = fresh_model()
        m.zero_grad()
        for r in range(R):
            lq = log_q[cols[r]] if corrected else torch.zeros(B)
            batch = (torch.eye(U)[rows[r]], torch.eye(N)[cols[r]], None, lq, None, cols[r])
            (two_tower_softmax_loss(m, batch) / R).backward()
        g = flat_grad(m)
        return ((g / g.norm()) * ref).sum().item()

    plain, corrected = cosine_to_ref(False), cosine_to_ref(True)
    assert corrected > 0.9                          # xấp xỉ full softmax gần như khít
    assert corrected > plain + 0.3                  # khoảng cách thật là 0.45, biên an toàn


def test_softmax_loss_scales_with_temperature():
    from ai_core.training.loss_fns import two_tower_softmax_loss

    batch = _softmax_batch([1, 2, 3, 4], [-2.0] * 4)
    hot = two_tower_softmax_loss(_softmax_model(temperature=0.05), batch)
    cold = two_tower_softmax_loss(_softmax_model(temperature=1.0), batch)
    assert not torch.allclose(hot, cold)


# ---------- feature build ----------

def test_build_features_gives_item_tower_log_popularity():
    """Baseline popularity thắng chỉ nhờ tín hiệu này; model phải có nó ở item tower."""
    from ai_core.training.datasets import build_features

    genres = {i: torch.zeros(19) for i in (1, 2, 3)}
    ratings = [(1, 1, t) for t in range(10)] + [(2, 2, 99), (2, 1, 100)]   # item 3 chưa ai thích
    user_feat, video_feat = build_features(ratings, genres)

    assert video_feat[1].numel() == 19 + 1 + 3                     # genre + log-pop + one-hot item
    pop = {i: video_feat[i][19].item() for i in (1, 2, 3)}
    assert pop[1] > pop[2] > pop[3]
    assert pop[3] == 0.0 and 0.0 <= pop[1] <= 1.0                  # chuẩn hoá [0,1]; 0 lượt = 0
    assert set(user_feat) == {1, 2}


def test_build_features_drops_user_genre_by_default():
    """Genre trung bình gần như đồng nhất giữa user → nhiễu; mặc định user tower chỉ one-hot."""
    from ai_core.training.datasets import build_features

    genres = {i: torch.zeros(19) for i in (1, 2)}
    ratings = [(1, 1, 0), (2, 2, 1)]
    user_plain, _ = build_features(ratings, genres)
    user_genre, _ = build_features(ratings, genres, use_user_genre=True)

    assert user_plain[1].numel() == 2                              # one-hot 2 user
    assert user_genre[1].numel() == 19 + 2


# ---------- split per-user ----------

def test_leave_last_k_split_keeps_every_user_on_both_sides():
    """Điểm khác biệt với time_split: global cut để lại 91/943 user, per-user giữ đủ user."""
    from ai_core.training.datasets import leave_last_k_split, time_split

    # user 1 hoạt động sớm, user 2 hoạt động muộn → global cut đẩy user 1 ra khỏi held-out.
    ratings = [(1, i, i) for i in range(1, 11)] + [(2, i, 100 + i) for i in range(1, 11)]
    _, held_global = time_split(ratings, test_ratio=0.2)
    assert {u for u, _, _ in held_global} == {2}                  # user 1 mất hẳn

    train, held = leave_last_k_split(ratings, k=3)
    assert {u for u, _, _ in train} == {1, 2}
    assert {u for u, _, _ in held} == {1, 2}                     # cả hai user đều được chấm


def test_leave_last_k_split_holds_out_the_newest_k_per_user():
    """Không được train trên tương lai của chính user đó."""
    from ai_core.training.datasets import leave_last_k_split

    ratings = [(1, 10, 5), (1, 11, 1), (1, 12, 9), (1, 13, 3)]    # cố tình xáo thứ tự
    train, held = leave_last_k_split(ratings, k=2)

    assert {i for _, i, _ in held} == {12, 10}                    # ts 9 và 5 = hai mốc mới nhất
    assert {i for _, i, _ in train} == {11, 13}
    assert max(ts for _, _, ts in train) < min(ts for _, _, ts in held)


def test_leave_last_k_split_is_independent_of_input_order():
    """Timestamp TRÙNG là chuyện thường ở MovieLens (nhiều rating cùng một giây, cùng user).

    Sort chỉ theo timestamp + sort ổn định của Python = thứ tự dòng trùng ts thừa hưởng thứ tự
    input, nên đổi thứ tự đọc u.data là đổi split → số liệu luận án không tái lập. Đã gặp thật:
    audit trên dữ liệu thật báo 'split phu thuoc thu tu input' trước khi thêm item_id tiebreaker.
    Fixture BẮT BUỘC có tie, không thì test vô nghĩa.
    """
    import random
    from ai_core.training.datasets import leave_last_k_split, time_split

    # user 1: 4 dòng cùng ts=100 → tie ngay tại biên k=2.
    ratings = [(1, 5, 100), (1, 6, 100), (1, 7, 100), (1, 8, 100),
               (2, 5, 200), (2, 6, 200), (2, 7, 201)]
    shuffled = ratings[:]
    random.Random(7).shuffle(shuffled)
    assert shuffled != ratings                                   # thứ tự thật sự khác

    tr_a, held_a = leave_last_k_split(ratings, k=2)
    tr_b, held_b = leave_last_k_split(shuffled, k=2)
    assert set(held_a) == set(held_b) and set(tr_a) == set(tr_b)
    assert held_a == held_b and tr_a == tr_b                     # kể cả thứ tự trả về

    assert time_split(ratings, 0.5) == time_split(shuffled, 0.5)  # cùng lỗi, cùng cách sửa


def test_leave_last_k_split_keeps_short_history_users_in_train():
    """User ≤ k tương tác: giữ hết ở train để vẫn có embedding + feature, không chấm user đó."""
    from ai_core.training.datasets import leave_last_k_split

    ratings = [(1, i, i) for i in range(1, 6)] + [(2, 9, 50), (2, 8, 51)]
    train, held = leave_last_k_split(ratings, k=3)

    assert {u for u, _, _ in held} == {1}                         # user 2 chỉ có 2 < 3
    assert sorted(i for u, i, _ in train if u == 2) == [8, 9]     # nguyên vẹn ở train
    assert len(train) + len(held) == len(ratings)                 # không mất dòng nào


# ---------- metric & cổng T1.7 ----------

def test_recall_at_k_is_fraction_of_relevant_not_hit_rate():
    """Recall@k = |rel ∩ top-k| / |rel|. Hit-rate (≥1 hit → 1) làm số cao gấp ~10× ở Two-Tower."""
    from ai_core.scripts.evaluate import recall_at_k

    assert recall_at_k([[1, 9, 8]], [{1, 2}], k=3) == 0.5          # 1 trong 2 relevant
    assert recall_at_k([[1, 2, 8]], [{1, 2}], k=3) == 1.0


def test_eval_recommender_defaults_to_every_eligible_user():
    """n_users=None → chấm hết, không còn 'tập 300 user nào' để lệch giữa hai lần đo."""
    from ai_core.scripts.evaluate import eval_recommender

    video_features = {i: torch.eye(4)[i - 1] for i in range(1, 5)}
    user_features = {u: torch.ones(3) for u in (1, 2, 3)}
    train_rows = [(u, 1, u) for u in (1, 2, 3)]
    test_rows = [(u, 4, 10) for u in (1, 2, 3)]

    class Dummy:
        def eval(self): pass
        def user_embed(self, x): return torch.ones(x.shape[0], 4)
        def video_embed(self, x): return x

    m = eval_recommender(Dummy(), user_features, video_features, train_rows, test_rows, k=2)
    assert m["n_users"] == m["n_eligible"] == 3


def test_gate_verdict_follows_ndcg_only():
    """evaluation_plan §1 cột 'Mục tiêu chấp nhận' của Two-Tower = NDCG@10 vượt popularity."""
    from ai_core.scripts.evaluate import format_recommender_report

    out = format_recommender_report({
        "n_users": 280, "n_eligible": 280,
        "model_ndcg": 0.30, "model_recall": 0.05,      # NDCG thắng, Recall thua
        "pop_ndcg": 0.26, "pop_recall": 0.07,
    })
    assert "NDCG (cổng T1.7): PASS" in out
    assert "FAIL" not in out


def test_aggregate_runs_reports_mean_and_std():
    """evaluation_plan §0.3: Two-Tower phải 3 lần chạy mean ± std, không kết luận từ 1 seed."""
    from ai_core.scripts.evaluate import aggregate_runs, format_seed_report

    runs = [{"model_ndcg": 0.20, "pop_ndcg": 0.26, "model_recall": 0.05, "pop_recall": 0.07},
            {"model_ndcg": 0.30, "pop_ndcg": 0.26, "model_recall": 0.07, "pop_recall": 0.07}]
    agg = aggregate_runs(runs)

    assert agg["n_runs"] == 2
    assert abs(agg["model_ndcg"] - 0.25) < 1e-9
    assert agg["model_ndcg_std"] > 0 and agg["pop_ndcg_std"] == 0.0
    assert "gap NDCG=-0.0100" in format_seed_report(agg)
