"""AI-03a: package Claude-drafted summaries (CLAUDE_PROPOSED) for the 40 real-domain clips. Never a training target until HUMAN_VERIFIED."""
import hashlib
import json
import sys
import unicodedata
from pathlib import Path

ROOT = Path("E:/traning_ai")
sys.path[:0] = [str(ROOT / "inference-service"), str(ROOT / "ai-core")]
from ai_core.scripts.prepare_aligned_summary import has_sentence_ending  # noqa: E402
from app.registry import ModelRegistry  # noqa: E402  (same BPE rebuild the inference service uses)

SRC = Path("D:/data_training_ai/minigpt_domain_v1_20261019/whisper_review_v1/received_860f8068d0bd/reviewed_whisper_domain_v1.json")
SRC_SHA = "860f8068d0bd16398bbf1d2fd99bc24e276e01c55ca6b5343c78df757ca9e5a4"
OUT = Path("D:/data_training_ai/minigpt_domain_v1_20261019/claude_summaries_v1")

# (summary, note) — note records what was omitted/normalised because the reviewed transcript is still noisy.
S = {
 "dom_wzKzkenrYew_1": ("Kim loại sản xuất trong nước đáp ứng khoảng 85–90% nhu cầu sản xuất xe máy, 20–40% cho ô tô và khoảng 10% linh kiện cho công nghiệp công nghệ cao. Viện Nghiên cứu Cơ khí nhận định ngành cơ khí Việt Nam đi sau nhưng đang phát triển.", "bỏ chi tiết 'thịp bị đồng bộ'/máy nông nghiệp; câu cuối bị cắt"),
 "dom_f7VbxhaVtfk_1": ("Đồng Tháp đẩy mạnh xúc tiến thương mại để nâng thu nhập nông thôn; nhiều sản phẩm OCOP của tỉnh đã vào các hệ thống bán lẻ lớn và các sàn thương mại điện tử như Lazada, Shopee.", "chuẩn hóa 'Ocop' → OCOP; bỏ tên siêu thị/sàn bị méo"),
 "dom_wYRFi4-KWek_2": ("Giá trị thương hiệu tăng trưởng hai con số trong 5 năm qua; ngoài doanh nghiệp lớn, nhiều doanh nghiệp vừa và nhỏ trong công nghệ, cơ khí, đổi mới sáng tạo cũng tăng trưởng nhanh, với đóng góp quan trọng của giá trị thương hiệu.", ""),
 "dom_vlSB_Kyx_kA_1": ("Thành phố xác định vùng đỏ có nguy cơ cao, đóng 30 đường kết nối và lập 23 chốt kiểm soát trực 24/24 do công an chủ trì, đồng thời yêu cầu không để đứt gãy chuỗi cung ứng hàng hóa thiết yếu.", "bỏ chi tiết '53 đường qua sông kênh'"),
 "dom_vlSB_Kyx_kA_2": ("Hà Nội đóng 30 đường kết nối từ vùng 1 sang vùng 2, 3, hạn chế tối đa di chuyển liên vùng, kiểm soát chặt và chia sẻ chi phí xét nghiệm khi cần đi lại; các quận, huyện quyết định việc phòng, chống dịch.", ""),
 "dom_soszp1_iK0E_1": ("Một hộ dân cho rằng mức đền bù quá thấp, chưa phù hợp luật đất đai; gia đình đã cải tạo vùng đất trũng sâu 7–8 mét từ khoảng 40 năm trước và ủng hộ dự án mở đường Đặng Thai Mai.", "bỏ năm luật '2020' (không chắc); câu cuối bị cắt"),
 "dom_b3Y2ckFkva0_2": ("Chưa có quy định bắt buộc chủ đầu tư condotel bảo lãnh nghĩa vụ tài chính với khách hàng, cá nhân nước ngoài chưa được mua căn hộ condotel; Hiệp hội Bất động sản TP.HCM kiến nghị sửa Luật Đất đai để phát triển du lịch.", "chuẩn hóa 'cơ đô theo' → condotel"),
 "dom_x1x03SI8jV0_1": ("Vụ tranh chấp 477,8 m² đất có nguồn gốc do ông Nguyễn Tấn Tạo mua năm 1945, sau cho ông Hội cất nhà ở; ông Hội mất năm 1951, đến năm 1987 gia đình bà Đỗ Thị Lan kê khai đăng ký nhà đất.", "bỏ 'La Chủ trì Chùa Tây Tạng' (không rõ)"),
 "dom_x1x03SI8jV0_2": ("Liên quan vụ việc của ông Trung và bà Lan, ngày 7/4/2010 UBND tỉnh Bình Dương ra quyết định số 1041 hủy bỏ quyết định số 5562 ngày 2/10/2002 và quyết định số 2606.", "bỏ mốc năm mâu thuẫn ('vụ kiện 2016' vs '3 năm sau 2010'); 'quy định' → quyết định (QĐ-UBND)"),
 "dom_Q95eDJlAhyI_1": ("Báo Tuổi trẻ Thủ đô và Ngân hàng Hợp tác xã Việt Nam phối hợp với Tỉnh đoàn Lào Cai giúp vợ chồng ông Tân, bà Xiếc có mái nhà vững chãi sau khi bão số 10 gây ảnh hưởng nghiêm trọng.", "tên người theo transcript, chưa kiểm audio"),
 "dom_any7NAvA7AY_1": ("Chương trình tư vấn hướng nghiệp: đại diện các trường đại học cập nhật phương án tuyển sinh năm 2025, mốc thời gian và phương thức xét tuyển mới; chuyên gia giải đáp câu hỏi của học sinh về chọn ngành, chọn trường.", ""),
 "dom_any7NAvA7AY_2": ("Một thầy giáo cho rằng AI dù phát triển đến đâu cũng không thể thay thế con người; khu vực tư vấn tuyển sinh giới thiệu chỉ tiêu, học phí, chương trình đào tạo và học bổng để học sinh chọn lựa phù hợp.", ""),
 "dom_DNM7BTlJnxA_2": ("Giải báo chí thu hút 345 tác phẩm của 48 cơ quan báo chí, gồm 7 cơ quan của Hà Nội và 41 cơ quan Trung ương, bộ ngành, địa phương, góp phần phát huy văn hóa Thăng Long – Hà Nội.", ""),
 "dom_cvZqE-2LEG8_1": ("Do khí hậu lạnh và khô, búp chè ở đây nhỏ; một thương hiệu trà sức khỏe chuyên sâu mang sứ mệnh bảo tồn và phát triển.", "transcript rất nhiễu ('Đó đại năng thạch búp', 'trà 60 tuổi'); user để trống summary — cần nghe lại"),
 "dom_Hew7T-qHV-8_1": ("Lời chào và kết thúc bản tin 18 giờ trên kênh YouTube Báo Sài Gòn Đầu tư Tài chính, mời khán giả đăng ký kênh để theo dõi tin kinh tế, đời sống.", "clip chỉ có lời chào kênh"),
 "dom_6CDgfB3MhmA_1": ("Mở đầu bản tin 18 giờ của kênh YouTube Sài Gòn Đầu tư Tài chính; tin đầu tiên về quỹ đầu tư ngoại muốn rót hàng tỷ USD vào chứng khoán Việt Nam.", "chuẩn hóa 'xây gom' → Sài Gòn"),
 "dom_6CDgfB3MhmA_2": ("Lãi suất tiết kiệm được chào ở mức 9,2–9,4%/năm, có thể tới 9,5% với khoản gửi lớn; Ngân hàng Nhà nước cho biết tiền gửi của khách hàng cá nhân tiếp tục tăng mạnh trong tháng 7.", ""),
 "dom_NNbXoXEWEfY_1": ("Các sở ngành TP.HCM nêu giải pháp thúc đẩy tăng trưởng: Sở Công Thương tổ chức 7 sự kiện kết nối cung cầu, Sở Xây dựng đẩy mạnh giải ngân đầu tư công cho dự án trọng điểm, hải quan triển khai đợt cao điểm 100 ngày.", "chuẩn hóa 'sửa ngành'/'dạy pháp' → sở ngành/giải pháp"),
 "dom_NNbXoXEWEfY_2": ("Thống kê TP.HCM cho biết tổng sản phẩm trên địa bàn quý III tăng 9,86% so với cùng kỳ, 10,08% nếu loại trừ dầu khí; khu vực nông, lâm nghiệp và thủy sản tăng 3,4%.", "bỏ năm mâu thuẫn (2016/2026) và '9 tỷ USD tăng 323%' (thiếu ngữ cảnh)"),
 "dom_9BHoS_sDlUw_1": ("Lời chào mở đầu bản tin 18 giờ của kênh YouTube Sài Gòn Đầu tư Tài chính, cập nhật tin kinh tế, thị trường và đời sống dân sinh trong và ngoài nước.", "clip chỉ có lời chào kênh; transcript trùng dom_p7FlzMrLDSo_1"),
 "dom_p7FlzMrLDSo_1": ("Lời chào mở đầu bản tin 18 giờ của kênh YouTube Sài Gòn Đầu tư Tài chính, cập nhật tin kinh tế, thị trường và đời sống dân sinh trong và ngoài nước.", "transcript trùng hệt dom_9BHoS_sDlUw_1 → summary trùng; người duyệt nên loại/tách đoạn (intake chặn trùng train/val)"),
 "dom_p7FlzMrLDSo_2": ("Dự thảo quy định khi giá đầu mối tăng, đơn vị phân phối không bắt buộc tăng tương ứng; Bộ Công Thương điều chỉnh chi phí định mức theo CPI, doanh nghiệp báo cáo chi phí thực tế hằng năm và kiểm toán độc lập 3 năm một lần.", "bỏ 'chênh lệch không quá 200%' (không chắc)"),
 "dom_wzKzkenrYew_2": ("Doanh nghiệp cơ khí dùng công nghệ CNC và linh kiện nhập khẩu để tối ưu chi phí, nâng tiêu chuẩn sản xuất theo chuẩn quốc tế; ngành thang máy Việt Nam có nhu cầu rất cao và doanh nghiệp trong nước muốn làm sản phẩm chất lượng cho người Việt.", "bỏ 'Inaugz' (không rõ)"),
 "dom_f7VbxhaVtfk_2": ("Ngoài thương mại điện tử và điểm bán OCOP, gian hàng Đồng Tháp tại các hội chợ thu hút doanh nghiệp với sản phẩm đặc trưng chế biến từ sen và xoài, được người tiêu dùng ưa thích.", ""),
 "dom_wYRFi4-KWek_1": ("Thương hiệu quốc gia Việt Nam liên tục tăng giá trị và thứ hạng quốc tế; ngoài kinh tế vĩ mô, chính trị, văn hóa, cộng đồng doanh nghiệp đóng góp quan trọng vì thương hiệu doanh nghiệp nâng giá trị thương hiệu quốc gia.", ""),
 "dom_-1Is0o2ZWk0_1": ("Tổng kim ngạch xuất nhập khẩu của Việt Nam lần đầu đạt 930,5 tỷ USD, mức cao nhất từ trước đến nay; năm 2025 nền kinh tế phục hồi kiên cường và lạm phát được kiểm soát.", "bỏ 'lạm phát 31,3%' (gần như chắc chắn méo)"),
 "dom_-1Is0o2ZWk0_2": ("Khoảng 75–85% nguyên vật liệu được đảm bảo trong nước theo yêu cầu các hiệp định; Việt Nam là một trong những nền kinh tế mở nhất thế giới với mạng lưới FTA rộng, gồm CPTPP và hiệp định với Liên minh châu Âu.", "chuẩn hóa 'CPTTP' → CPTPP"),
 "dom_uY0zUhWOLJM_1": ("Triển lãm giới thiệu công nghệ, máy móc về cơ khí chế tạo, hàn cắt, gia công kim loại, tự động hóa, thiết bị điện và dây cáp; doanh nghiệp tham gia có giải pháp sẵn sàng cho các dự án trọng điểm quốc gia như dự án tàu điện.", "bỏ 'tàu điện Châu Âu' (không rõ)"),
 "dom_uY0zUhWOLJM_2": ("Mô hình triển lãm đa chuyên đề tạo hệ sinh thái kết nối cho ngành công nghiệp, từ máy móc, tự động hóa, dụng cụ cầm tay đến hàn cắt, gia công kim loại và dây cáp điện; đơn vị tổ chức đánh giá hiệu quả rất tốt.", "bỏ 'IT, SPO' (không rõ)"),
 "dom_soszp1_iK0E_2": ("Người dân có đăng ký đất đai và nộp thuế đất phi nông nghiệp thì công trình, tài sản gắn liền với đất được pháp luật bảo vệ và phải được bồi thường đầy đủ khi thu hồi đất mở rộng đường.", "bỏ '980' đầu câu (không rõ năm)"),
 "dom_b3Y2ckFkva0_1": ("Ý kiến cho rằng vấn đề xuất phát từ lợi ích chủ đầu tư condotel: lợi nhuận rất lớn, giá bán ngang căn hộ cao cấp trong khi nghĩa vụ nộp tiền sử dụng đất chưa tương xứng, và họ muốn bán nhanh, chốt lời nhanh.", "chuẩn hóa 'Cô đối theo' → condotel"),
 "dom_qoYByuKMIv4_1": ("Trước hình ảnh người giúp việc đánh trẻ sơ sinh, chuyên gia pháp luật cho rằng có lỗ hổng lớn: người giúp việc làm việc thường xuyên, liên tục nhưng không xác lập hợp đồng.", ""),
 "dom_qoYByuKMIv4_2": ("Chuyên gia đề nghị gia đình kiểm tra nhân thân người giúp việc, pháp luật cần quy định kiểm tra sức khỏe về bệnh truyền nhiễm và tiền sử bệnh tâm thần; người dẫn hỏi về giải pháp ngăn chặn của cơ quan chức năng.", ""),
 "dom_Q95eDJlAhyI_2": ("Báo Tuổi trẻ Thủ đô trao suất hỗ trợ 60 triệu đồng cho hai ông bà, họ trích 1 triệu đồng giúp gia đình khó khăn khác; đoàn công tác còn chăm lo cho thế hệ tương lai.", ""),
 "dom_sTeS-7km_NM_1": ("Nhà nước đã có nhiều chính sách cho công tác phát triển nguồn nhân lực của Thủ đô và đất nước, nhưng sự mất cân bằng trong phân bổ nhân lực hiện nay vẫn gây lãng phí.", "câu về nhận thức học sinh bị cắt → bỏ; 'nguồn nhân lực' suy từ ngữ cảnh"),
 "dom_sTeS-7km_NM_2": ("Bộ Giáo dục và Đào tạo lưu ý học sinh tham gia xét tuyển sớm cần nghiên cứu thông tin tuyển sinh trên website các trường để không bỏ lỡ hồ sơ và thời hạn; học sinh còn được chuyên gia các trường tư vấn.", ""),
 "dom_DNM7BTlJnxA_1": ("Thăng Long – Hà Nội được khẳng định là vùng đất địa linh nhân kiệt với giá trị nghìn năm; các giá trị văn hóa là nền tảng, động lực và nguồn lực cho xây dựng, phát triển hôm nay và mai sau.", ""),
 "dom_cvZqE-2LEG8_2": ("Trà Dragon Tea Suối Giàng không chỉ là sản phẩm mà còn là biểu tượng cho nỗ lực phát triển kinh tế vùng, bảo vệ môi trường và gìn giữ bản sắc văn hóa dân tộc thiểu số.", ""),
 "dom_Hew7T-qHV-8_2": ("Quốc hội giám sát các dự án hạ tầng trọng điểm như sân bay Long Thành, đường sắt tốc độ cao Bắc – Nam và tuyến đường sắt Lào Cai – Hà Nội – Hải Phòng; sân bay Long Thành có quy mô khoảng 5.000 ha.", "bỏ 'tổng mức đầu tư gần 337.000 nghìn tỷ' (méo đơn vị)"),
 "dom_9BHoS_sDlUw_2": ("Mức độ quan tâm tìm kiếm bất động sản tăng 3,5% so với quý trước; nhà dưới 5 tỷ đồng thu hút 37% lượng tìm kiếm, còn phân khúc 5–10 tỷ đồng chiếm 59% tin đăng bán nhưng chỉ tiếp cận 45% nhu cầu.", "bỏ '922%' (méo); user để trống summary — cần nghe lại"),
}


def sha(b):
    return hashlib.sha256(b).hexdigest()


def main():
    raw = SRC.read_bytes()
    assert sha(raw) == SRC_SHA, "reviewed export changed"
    data = json.loads(raw)
    if OUT.exists():
        raise SystemExit(f"{OUT} exists — never overwrite")
    tok = ModelRegistry._rebuild_tokenizer(json.loads((ROOT / "ai-core/checkpoints/minigpt/bpe_vocab.json").read_text(encoding="utf-8")))
    ids = [r["sample_id"] for r in data["records"]]
    assert set(ids) == set(S) and len(ids) == 40, "summary set must match the 40 clips exactly"
    records = []
    for r in data["records"]:
        summary, note = S[r["sample_id"]]
        summary = unicodedata.normalize("NFC", summary)
        n = len(tok.encode(summary))
        assert n + 1 <= 96, (r["sample_id"], n)
        assert has_sentence_ending(summary), r["sample_id"]
        records.append({
            "sample_id": r["sample_id"], "audio_sha256": r["audio_sha256"], "video_sha256": r["video_sha256"],
            "source_transcript_sha256": sha(unicodedata.normalize("NFC", r["transcript"]).encode("utf-8")),
            "summary": summary, "bpe_tokens": n, "notes": note,
            "label": "CLAUDE_PROPOSED", "provenance": "claude_drafted_unverified", "verified": False,
            "author": "Claude (claude-opus-5-5), AI lane", "created": "2026-10-26",
            "method": "text-only from user-reviewed transcript; no audio listening; no external model output",
        })
    payload = {"protocol": "claude-summary-proposal-v1", "status": "CLAUDE_PROPOSED — NOT A TRAINING/EVAL TARGET UNTIL HUMAN_VERIFIED",
               "source_export": str(SRC), "source_export_sha256": SRC_SHA, "training_ready": False, "records": records}
    OUT.mkdir(parents=True)
    body = json.dumps(payload, ensure_ascii=False, indent=1).encode("utf-8")
    (OUT / "claude_summaries_v1.json").write_bytes(body)
    print(json.dumps({"file": str(OUT / "claude_summaries_v1.json"), "sha256": sha(body), "n": len(records),
                      "max_bpe": max(x["bpe_tokens"] for x in records), "mean_bpe": round(sum(x["bpe_tokens"] for x in records) / 40, 1),
                      "with_notes": sum(1 for x in records if x["notes"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
