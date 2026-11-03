# Xóa tóm tắt AI bịa (user duyệt 2026-11-03: "xóa tóm tắt")

Phạm vi: video chưa xóa có tóm tắt AI khác rỗng, `summary_status != approved`, và `transcript_quality < 0.7` hoặc null (API 0.10.0).
Cách: `PUT /api/cms/videos/{id}/summary {"summary":""}` (luồng app, status draft). Không đụng phụ đề, tiêu đề, video, clip.

| video | phụ đề | tóm tắt cũ (bịa) |
|---|---|---|
| vid_dm3nf6fi23us T4.1-REAL-AI-SMOKE | null | 'Tương truyền' |
| vid_dm46jsx30bah Tạo video chiến đấu.mp4 | 0.6 | 'TE' |
| vid_dmh4b8ymqbtw sample_01.mp4 | 0.647 | (GDVN) … 87 ký tự |
| vid_dmh5o652juum dom_-1Is0o2ZWk0_1.mp4 | 0.495 | (ĐTCK-online) … 236 ký tự |
| vid_dmlfc92ipi6w vleague_danang_haiphong_5phut.mp4 | 0.6 | (Dân Việt) - Bò được xây dựng … 205 ký tự |

5/5 HTTP 200; `after.json` = tất cả summary rỗng, các trường khác không đổi. Bản gốc đầy đủ: `before.json` (khôi phục = PUT lại chuỗi đó).
Không có tóm tắt đã duyệt nào trong phạm vi. API công khai không hiện tóm tắt chưa duyệt.
