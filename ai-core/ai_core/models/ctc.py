"""CTC loss (log-alpha forward DP) + greedy/beam decode tự cài — plan 01 §6.3.

Đối chiếu torch.nn.CTCLoss trong test_ctc_parity (atol 1e-4).
Quy ước: blank = 0; log_probs đã log_softmax, shape (T, B, C) hoặc (B, T, C).
"""

import math

import torch

_NEG_INF = -1e30


def _logsumexp2(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    m = torch.maximum(a, b)
    m = torch.where(torch.isinf(m), torch.zeros_like(m), m)
    return m + torch.log(torch.exp(a - m) + torch.exp(b - m))


def _logaddexp(a: float, b: float) -> float:
    if a <= _NEG_INF:
        return b
    if b <= _NEG_INF:
        return a
    m = max(a, b)
    return m + math.log(math.exp(a - m) + math.exp(b - m))


def ctc_loss(
    log_probs: torch.Tensor,          # (T, B, C) log_softmax
    targets: torch.Tensor,            # (B, S) hoặc (sum_S,) concat
    input_lengths: torch.Tensor,      # (B,)
    target_lengths: torch.Tensor,     # (B,)
    blank: int = 0,
    reduction: str = "mean",
) -> torch.Tensor:
    """CTC negative log-likelihood bằng quy hoạch động log-alpha (chia cho target_length).

    VECTOR HOÁ theo (batch, state). Bản đầu là vòng lặp Python ba tầng `b × t × s`, và chính nó làm
    T1.4 không train được: batch 16 câu VIVOS (T′≈134, L=121) ra 259.424 vòng lặp, mỗi vòng tạo ~6
    tensor autograd 0-chiều → ~1,5 triệu node đồ thị mỗi step. Đo được **318 giây/step** rồi
    `RuntimeError: bad allocation`; hai kernel Kaggle (v28, v29) bị huỷ ở giới hạn 9 giờ mà chưa
    kịp tới step 200.

    `test_ctc_parity` vẫn pass suốt vì nó chấm T=20, B=3, S≤6 — 780 vòng lặp, xong trong vài ms.
    Nó kiểm tính ĐÚNG, không kiểm tính KHẢ THI.

    Vòng lặp theo `t` giữ nguyên (đệ quy thời gian, không tránh được); `b` và `s` chạy song song
    dưới dạng tensor (B, L) nên số phép ở tầng Python giảm từ B·T·L xuống T.
    """
    T, B, C = log_probs.shape
    device, dtype = log_probs.device, log_probs.dtype

    tgt_len = target_lengths.to(device=device, dtype=torch.long)
    inp_len = input_lengths.to(device=device, dtype=torch.long).clamp(max=T)
    s_max = int(tgt_len.max().item())
    L = 2 * s_max + 1

    # ext: (B, L) chuỗi nhãn mở rộng blank-xen-kẽ, pad blank cho câu ngắn hơn.
    ext = torch.full((B, L), blank, dtype=torch.long, device=device)
    for b in range(B):                                # B nhỏ (≤ batch size), không phải nút thắt
        sb = int(tgt_len[b].item())
        if sb == 0:
            continue
        y = targets[b, :sb] if targets.ndim == 2 else \
            targets[int(tgt_len[:b].sum().item()):][:sb]
        ext[b, 1:2 * sb:2] = y.to(device=device, dtype=torch.long)

    ar = torch.arange(L, device=device)
    valid = ar.unsqueeze(0) < (2 * tgt_len + 1).unsqueeze(1)           # (B, L)
    NEG = torch.tensor(_NEG_INF, dtype=dtype, device=device)
    neg_col = NEG.expand(B, 1)

    # Bước nhảy 2 chỉ hợp lệ khi ext[s] khác blank VÀ khác ext[s-2].
    ext_m2 = torch.cat([torch.full((B, 2), blank, dtype=torch.long, device=device), ext[:, :-2]], 1)
    allow2 = (ext != blank) & (ext != ext_m2) & (ar.unsqueeze(0) >= 2)

    lp0 = log_probs[0].gather(1, ext)                                  # (B, L)
    init = torch.where(ar.unsqueeze(0) <= 1, lp0, NEG.expand(B, L))
    alpha = torch.where(valid, init, NEG.expand(B, L))

    for t in range(1, int(inp_len.max().item())):
        a1 = torch.cat([neg_col, alpha[:, :-1]], dim=1)
        a2 = torch.cat([neg_col, neg_col, alpha[:, :-2]], dim=1) if L > 2 else NEG.expand(B, L)
        m = torch.logaddexp(alpha, a1)
        m = torch.logaddexp(m, torch.where(allow2, a2, NEG.expand(B, L)))
        nxt = torch.where(valid, m + log_probs[t].gather(1, ext), NEG.expand(B, L))
        # Câu đã hết frame thì đóng băng alpha, không cho tiến thêm.
        alpha = torch.where((inp_len > t).unsqueeze(1), nxt, alpha)

    last = 2 * tgt_len                                                 # chỉ số L_b − 1
    end1 = alpha.gather(1, last.unsqueeze(1)).squeeze(1)
    end2 = alpha.gather(1, (last - 1).clamp(min=0).unsqueeze(1)).squeeze(1)
    ll = torch.where(tgt_len > 0, torch.logaddexp(end1, end2), end1)
    loss = -ll / tgt_len.clamp(min=1).to(dtype)
    if reduction == "mean":
        return loss.mean()
    if reduction == "sum":
        return loss.sum()
    return loss


def ctc_greedy_decode(log_probs: torch.Tensor, lengths: torch.Tensor, blank: int = 0) -> list[list[int]]:
    """Greedy: argmax mỗi frame, collapse repeat + bỏ blank. log_probs (B, T, C)."""
    best = log_probs.argmax(dim=-1)                    # (B, T)
    out = []
    for b in range(best.shape[0]):
        Tb = int(lengths[b].item())
        seq, prev = [], None
        for t in range(Tb):
            c = int(best[b, t].item())
            if c != blank and c != prev:
                seq.append(c)
            prev = c
        out.append(seq)
    return out


def ctc_segments(
    log_probs: torch.Tensor,          # (T, C) log_softmax của MỘT câu
    length: int,
    vocab: list[str],
    frame_sec: float,
    blank: int = 0,
    min_gap_frames: int = 5,
) -> list[dict]:
    """→ [{start, end, text}] có timestamp thật, cắt đoạn tại khoảng lặng (T1.4e).

    CTC cho alignment theo frame nên thời điểm phát ra từng ký tự là biết được: frame t′ ứng với
    `t′ * frame_sec` giây, với `frame_sec = hop / sr * subsample` (ở đây 160/16000 × 4 = 40 ms).

    Bản trước của `_real_asr` trả đúng MỘT segment `0 → len(audio)` cho cả câu. Nó khớp schema và
    trông như chạy được, nhưng không dựng nổi phụ đề: mọi dòng sẽ có cùng một mốc thời gian.

    Cắt đoạn ở chuỗi blank dài ≥ `min_gap_frames` (mặc định 5 frame = 200 ms) — khoảng lặng giữa các
    cụm từ. `frame_sec` truyền vào chứ không hardcode: subsample của encoder đổi thì mọi timestamp
    lệch theo, và lệch âm thầm.
    """
    best = log_probs[:length].argmax(dim=-1).tolist()
    segs: list[dict] = []
    cur: list[int] = []
    start_f: int | None = None
    gap = 0
    prev = None
    last_nonblank = 0

    def flush(end_f: int) -> None:
        if cur and start_f is not None:
            text = "".join(vocab[i] for i in cur if 0 < i < len(vocab)).strip()
            if text:
                segs.append({"start": round(start_f * frame_sec, 3),
                             "end": round(end_f * frame_sec, 3), "text": text})

    for t, c in enumerate(best):
        if c == blank:
            gap += 1
            if gap >= min_gap_frames and cur:
                flush(last_nonblank + 1)
                cur, start_f = [], None
        else:
            if c != prev:
                cur.append(c)
                if start_f is None:
                    start_f = t
            gap = 0
            last_nonblank = t
        prev = c
    flush(last_nonblank + 1)
    return segs


def ctc_beam_decode(
    log_probs: torch.Tensor,          # (B, T, C)
    lengths: torch.Tensor,
    beam_width: int = 10,
    blank: int = 0,
) -> list[list[int]]:
    """CTC prefix beam search chuẩn (Graves), không LM. Trả list token/sample.

    Mỗi prefix giữ (p_b, p_nb) = log-prob kết thúc bằng blank / non-blank.
    Toán pure-python (nhanh hơn tạo torch.tensor mỗi phép).
    """
    B, _, C = log_probs.shape
    results = []
    for b in range(B):
        Tb = int(lengths[b].item())
        lp = log_probs[b]                             # (T, C)
        beams: dict[tuple, tuple[float, float]] = {(): (0.0, _NEG_INF)}
        for t in range(Tb):
            row = lp[t].tolist()
            topc = sorted(range(C), key=lambda c: row[c], reverse=True)[:beam_width]
            if blank not in topc:
                topc.append(blank)
            next_beams: dict[tuple, tuple[float, float]] = {}

            def _get(pref: tuple) -> tuple[float, float]:
                return next_beams.get(pref, (_NEG_INF, _NEG_INF))

            for prefix, (pb, pnb) in beams.items():
                total = _logaddexp(pb, pnb)
                # blank → giữ prefix, kết thúc bằng blank
                nb_b, nb_nb = _get(prefix)
                next_beams[prefix] = (_logaddexp(nb_b, total + row[blank]), nb_nb)
                last = prefix[-1] if prefix else None
                for c in topc:
                    if c == blank:
                        continue
                    p = row[c]
                    if c == last:
                        # lặp ký tự: ở lại prefix (từ p_nb) + mở rộng (từ p_b)
                        cb, cnb = _get(prefix)
                        next_beams[prefix] = (cb, _logaddexp(cnb, pnb + p))
                        ext = prefix + (c,)
                        eb, enb = _get(ext)
                        next_beams[ext] = (eb, _logaddexp(enb, pb + p))
                    else:
                        ext = prefix + (c,)
                        eb, enb = _get(ext)
                        next_beams[ext] = (eb, _logaddexp(enb, total + p))
            beams = dict(sorted(next_beams.items(),
                                key=lambda kv: _logaddexp(kv[1][0], kv[1][1]),
                                reverse=True)[:beam_width])
        best = max(beams.items(), key=lambda kv: _logaddexp(kv[1][0], kv[1][1]))
        results.append(list(best[0]))
    return results
