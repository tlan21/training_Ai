"""MovieLens-100k → triple (user, pos, neg) BPR, split theo thời gian (dataset_spec §3.6)."""

import math
import random
from collections import Counter, defaultdict

import torch
from torch.utils.data import Dataset


def load_movielens_ratings(path: str) -> list[tuple[int, int, int]]:
    """u.data: user_id\titem_id\trating\ttimestamp → [(user, item, timestamp)] rating≥4 (positive)."""
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) < 4:
                continue
            u, i, r, ts = int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3])
            if r >= 4:
                out.append((u, i, ts))
    return out


def _ts_then_item(row):
    """Khoá sort TOÀN PHẦN (timestamp, item_id).

    Chỉ sort theo timestamp là chưa đủ: MovieLens có nhiều rating cùng một giây trong cùng user,
    sort của Python ổn định nên thứ tự các dòng trùng ts thừa hưởng thứ tự input → đổi thứ tự
    dòng trong u.data là đổi split (user có tie đúng ở biên thứ k rơi sang phía khác). Thêm
    item_id làm tiebreaker để split chỉ phụ thuộc DỮ LIỆU, không phụ thuộc thứ tự đọc file.
    """
    return (row[2], row[1])


def time_split(ratings: list[tuple[int, int, int]], test_ratio: float = 0.2):
    """Split theo timestamp GLOBAL: 80% cũ = train, 20% mới = test.

    Nhược điểm đo lường: cắt theo một mốc thời gian chung nên phần test chỉ còn user hoạt động ở
    cuối kỳ — MovieLens-100k rơi từ 943 user xuống 91 user đủ điều kiện eval, và phân phối
    train/test lệch theo thời gian. Dùng `leave_last_k_split` khi cần eval pool đầy đủ.
    """
    ratings = sorted(ratings, key=_ts_then_item)
    cut = int(len(ratings) * (1 - test_ratio))
    return ratings[:cut], ratings[cut:]


def leave_last_k_split(ratings: list[tuple[int, int, int]], k: int = 10):
    """Split theo thời gian TỪNG USER: k tương tác mới nhất của mỗi user → held-out.

    Vẫn tôn trọng thứ tự thời gian (không bao giờ train trên tương lai của chính user đó), nhưng
    mọi user đều có mặt ở CẢ train và held-out → eval pool không teo, và không lệch phân phối
    theo thời gian giữa hai phần như `time_split` gây ra.

    User có ≤ k tương tác: giữ toàn bộ ở train (không đủ dữ liệu để chia, và giữ lại thì user đó
    vẫn có embedding + feature).
    """
    by_user: dict[int, list] = defaultdict(list)
    for row in ratings:
        by_user[row[0]].append(row)
    train, held = [], []
    for rows in by_user.values():
        rows.sort(key=_ts_then_item)
        if len(rows) <= k:
            train.extend(rows)
        else:
            train.extend(rows[:-k])
            held.extend(rows[-k:])
    train.sort(key=_ts_then_item)
    held.sort(key=_ts_then_item)
    return train, held


def build_features(ratings, item_genres: dict, use_user_genre: bool = False):
    """→ (user_feat, video_feat) cho Two-Tower. CHỈ dùng `ratings` của train — không rò rỉ test.

    - video = [genre 19-d, log-popularity, one-hot item]
    - user  = [one-hot user] (+ genre trung bình item đã thích nếu `use_user_genre`)

    log-popularity: baseline popularity thắng CHỈ nhờ tín hiệu này, mà model không có cách nào
    biểu diễn "item này phổ biến" từ one-hot với ~10 positive/user. Cho thẳng vào item tower.
    Chuẩn hoá về [0,1] vì mọi chiều khác là 0/1; log(count) thô (~6.2) sẽ đè Linear đầu tiên.

    `use_user_genre=False` vì genre trung bình gần như đồng nhất giữa mọi user (mọi người đều
    xem Drama/Comedy) → chiều gần-vô-nghĩa, chỉ thêm nhiễu vào user tower.

    Dựng feature ở đây thay vì inline trong notebook: logic inline là nguyên nhân gốc của bug
    eval T1.7 (mỗi lần copy sang cell mới là một lần lệch).
    """
    item_ids = sorted(item_genres)
    n_genre = next(iter(item_genres.values())).numel()
    user_ids = sorted({u for u, _, _ in ratings})
    u_index = {u: k for k, u in enumerate(user_ids)}
    i_index = {i: k for k, i in enumerate(item_ids)}
    eye_u, eye_i = torch.eye(len(user_ids)), torch.eye(len(item_ids))

    counts = Counter(i for _, i, _ in ratings)
    max_log = math.log1p(max(counts.values())) if counts else 1.0
    video_feat = {
        i: torch.cat([
            item_genres[i],
            torch.tensor([math.log1p(counts.get(i, 0)) / max_log], dtype=torch.float32),
            eye_i[i_index[i]],
        ])
        for i in item_ids
    }

    user_feat = {u: eye_u[u_index[u]] for u in user_ids}
    if use_user_genre:
        acc = defaultdict(lambda: torch.zeros(n_genre))
        cnt = Counter()
        for u, i, _ in ratings:
            if i in item_genres:
                acc[u] += item_genres[i]
                cnt[u] += 1
        user_feat = {u: torch.cat([acc[u] / max(cnt[u], 1), user_feat[u]]) for u in user_ids}
    return user_feat, video_feat


class BPRTripleDataset(Dataset):
    """Item: (user_feat, pos_feat, neg_feat, log_q_pos, log_q_neg, pos_item_id).

    `neg_alpha` điều khiển phân phối sampling negative: q(i) ∝ count(i)^alpha.
    - alpha=0 → uniform (mặc định, giữ nguyên hành vi cũ).
    - alpha>0 → nghiêng về item phổ biến, để positive phổ biến thực sự phải cạnh tranh với
      negative phổ biến. Uniform negative gần như không bao giờ rơi vào vùng popular, nên model
      không học phân biệt ở đúng nơi ground-truth tập trung → thua cả popularity baseline.

    log_q trả kèm để loss trừ bias sampling. Với `two_tower_softmax_loss` (in-batch negative),
    candidate là positive của các hàng khác nên xuất hiện theo TẦN SUẤT DỮ LIỆU — log_q chỉ
    khớp tần suất đó khi `neg_alpha=1.0`, nên config softmax BẮT BUỘC alpha=1.0.

    pos_item_id trả kèm để loss mask accidental hit: item phổ biến lặp lại trong cùng batch,
    cột đó là positive thật của hàng khác, không mask thì gradient tự triệt tiêu đúng ở vùng
    popular — đúng nơi ground truth tập trung.
    """

    def __init__(
        self,
        ratings,
        user_features: dict,
        video_features: dict,
        n_items: int,
        seed: int = 1337,
        neg_alpha: float = 0.0,
    ):
        self.pos = [(u, i) for (u, i, _) in ratings]
        self.user_feat = user_features
        self.video_feat = video_features
        self.n_items = n_items
        self.neg_alpha = neg_alpha
        # Chỉ sample negative từ item CÓ feature (id có thể thưa/1-indexed như MovieLens) — tránh KeyError.
        self.item_ids = list(video_features.keys())
        self.user_pos = {}
        for u, i in self.pos:
            self.user_pos.setdefault(u, set()).add(i)
        self.rng = random.Random(seed)

        counts = {i: 0 for i in self.item_ids}
        for _, i in self.pos:
            if i in counts:
                counts[i] += 1
        if neg_alpha == 0.0:
            self._weights = None                    # rng.choice: nhanh hơn choices() có weight
            uniform = 1.0 / max(1, len(self.item_ids))
            self.log_q = {i: math.log(uniform) for i in self.item_ids}
        else:
            # +1 để item chưa từng xuất hiện trong train vẫn sample được (alpha>0 sẽ đưa về 0).
            w = [(counts[i] + 1) ** neg_alpha for i in self.item_ids]
            total = sum(w)
            self._weights = w
            self.log_q = {i: math.log(wi / total) for i, wi in zip(self.item_ids, w)}

    def __len__(self) -> int:
        return len(self.pos)

    def _sample_negative(self, u: int) -> int:
        excluded = self.user_pos.get(u, ())
        for _ in range(100):
            if self._weights is None:
                neg = self.rng.choice(self.item_ids)
            else:
                neg = self.rng.choices(self.item_ids, weights=self._weights, k=1)[0]
            if neg not in excluded:
                return neg
        # User đã thích gần hết catalog: rơi về quét tuyến tính thay vì lặp vô hạn.
        candidates = [i for i in self.item_ids if i not in excluded]
        if not candidates:
            raise ValueError(f"user {u} đã tương tác với toàn bộ item, không còn negative")
        return self.rng.choice(candidates)

    def __getitem__(self, idx: int):
        u, pos_i = self.pos[idx]
        neg_i = self._sample_negative(u)
        return (
            self.user_feat[u],
            self.video_feat[pos_i],
            self.video_feat[neg_i],
            torch.tensor(self.log_q[pos_i], dtype=torch.float32),
            torch.tensor(self.log_q[neg_i], dtype=torch.float32),
            torch.tensor(pos_i, dtype=torch.long),
        )
