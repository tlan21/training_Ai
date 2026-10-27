"""AI-02a: text-only CLAUDE_PROPOSED review aids for the 60 ASR expansion clips. Never labels: asr_gold.validate rejects them.

Claude cannot hear audio. Proposals only fix words the surrounding text makes near-certain; numbers, dates and identifiers are
never changed (flagged instead). Output goes next to the packet, never overwrites it.
"""
import hashlib
import json
import unicodedata
from pathlib import Path

BASE = Path("D:/data_training_ai/asr_domain_expansion_v2_20261022")
PACKET = BASE / "asr_review_v2/packet.json"
OUT = BASE / "claude_proposals_v1/asr_claude_proposals_v1.json"

HALLUCINATION = "Whisper hallucination signature (channel-outro phrase / 2-word stub) — listen once; if music/no speech, exclude the clip"
EX, FIX, LISTEN = "EXCLUDE_CANDIDATE", "CORRECTION", "LISTEN_ONLY"

# sample_id: (action, proposed_text | None, uncertain spans / notes, term_hints)
P = {
 "ext2_uvs5djEOuH4_1": (FIX, None, ["toàn đoạn là lời trẻ em; 'I went to the toilet and it has snow' có thể sai — nghe lại"], []),
 "ext2_uvs5djEOuH4_2": (FIX, "I am imitating you, you are saying. I don't know. Go to what you thought will come there. So, I just finished watching a video of a student teacher interaction on the Pantado's virtual learning platform. And I'm kind of saying I am",
                        ["hai câu đầu không rõ nghĩa", "cờ TIME_OUTSIDE_CLIP: lời cuối có thể nằm ngoài 20 s"], ["Pantado"]),
 "ext2_uvs5djEOuH4_3": (FIX, None, [], []),
 "ext2_uvs5djEOuH4_4": (FIX, None, ["cờ TIME_OUTSIDE_CLIP"], []),
 "ext2_uvs5djEOuH4_5": (FIX, "important because it allows students to build their confidence over time and to get over their initial like, \"shyness\" or their lack of confidence of speaking the English language. Because the lesson progressed from easy to more and more difficult, it was able to help the students",
                        [], []),
 "ext2_uvs5djEOuH4_6": (FIX, "navigate through the lesson and felt a sense of reward when they get through to the end. This is the reason why I think that Pantado's virtual learning system really works because it allows the kind of environment where students and teachers can work together and really just dive deep into the English language. So this is why I think that the virtual learning platform works with any age group.",
                        [], ["Pantado"]),
 "ext2_DL_TeDUv_LI_1": (LISTEN, None, ["nháp méo nặng"], ["tăng huyết áp", "đái tháo đường", "suy tim", "kiểm soát", "y học", "tiến bộ trong điều trị", "kỹ thuật"]),
 "ext2_DL_TeDUv_LI_2": (LISTEN, None, ["nháp méo nặng"], ["khuyến cáo", "chẩn đoán", "quản lý", "trí tuệ nhân tạo", "đột quỵ", "chống đông", "rung nhĩ", "phẫu thuật tim ít xâm lấn"]),
 "ext2_DL_TeDUv_LI_3": (LISTEN, None, ["nháp ngắn, méo"], ["kỹ thuật chuyên sâu"]),
 "ext2_mHatGR-AoLY_1": (FIX, "Nhiên linh một người có câu chả lời là có. Xã hội càng phát triển, ô tô càng phổ biến. Sẽ đến lúc tại Việt Nam mỗi gia đình sẽ có một chiếc ô tô. Thậm chí, mỗi thành viên trong gia đình sẽ sở hữu một xe. Cơ sở hạ tầng, đường xá giao thông ngày càng phát triển, hiện đại hơn. Một thị trường vô cùng tiềm năng để sản xuất",
                        ["câu đầu 'Nhiên linh một người có câu chả lời là có' giữ nguyên nháp", "'hiện đại hơn' (nháp: 'kênh đại hơn')"], []),
 "ext2_mHatGR-AoLY_2": (EX, None, [HALLUCINATION, "nháp chỉ 'Nguyễn Công Nguyễn Công' (SHORT_TRANSCRIPT)"], []),
 "ext2_mHatGR-AoLY_3": (FIX, "xuyên tuyển dụng nhưng cung vẫn không đủ cầu. Đặc biệt, cơn bão mang tên VinFast cấp tốc mang đến những tín hiệu vui cho ngành công nghệ kỹ thuật ô tô. Nhiều năm trở lại đây, công nghệ kỹ thuật ô tô luôn là một trong những ngành học được đông đảo thí sinh quan tâm tìm hiểu và lựa chọn trong mỗi mùa tuyển sinh. Giữa thế giới ngành nghề đang ngày một đa dạng hơn, sức khút biên vẫn cũng đau.",
                        ["'cấp tốc mang đến những tín hiệu vui' suy từ 'cấp tục mang đề những tỉnh hộ vui'", "câu cuối giữ nháp", "cờ TIME_OUTSIDE_CLIP"], ["VinFast"]),
 "ext2_mHatGR-AoLY_4": (FIX, "làm chủ công nghệ của người Việt. Nắm bắt được xu hướng phát triển và thị trường nguồn nhân lực vô cùng tiềm năng của ngành công nghệ kỹ thuật ô tô, Trường Đại học Đại Nam đã xây dựng đề án mở ngành công nghệ kỹ thuật ô tô và chính thức tuyển sinh trong năm 2021. Sinh viên ngành này sẽ trực tiếp thực hành trong môi trường doanh nghiệp ngay từ năm nhất và liên tục trong suốt quá trình học.",
                        ["'người Việt' (nháp: 'người chạy việt')", "năm '2021' giữ nguyên — nghe xác nhận"], ["Đại Nam"]),
 "ext2_mHatGR-AoLY_5": (FIX, "thực tế chương nhiệm, hiện đại và đầu ra cho sinh viên. Đây là tiền đề vô cùng quan trọng để sinh viên ngành công nghệ kỹ thuật ô tô Trường Đại học Đại Nam được rèn nghề ngay trên ghế nhà trường. Ra trường có thể làm được việc ngay tại doanh nghiệp, không phải đào tạo lại. Trong thời gian học, sinh viên ngành công nghệ kỹ thuật ô tô Đại học Đại Nam sẽ được trang bị bài bản các kiến thức về cơ khí.",
                        ["'thực tế chương nhiệm' giữ nháp (có thể 'chuyên nghiệp')", "cờ REPEATED_8_WORD_SEQUENCE: cụm 'sinh viên ngành công nghệ kỹ thuật ô tô' lặp hợp lệ", "cờ TIME_OUTSIDE_CLIP"], ["Đại Nam"]),
 "ext2_mHatGR-AoLY_6": (FIX, "và các tình các kỹ năng mềm, tin học và ngoại ngữ. Đặc biệt, sinh viên ngành công nghệ kỹ thuật ô tô Đại Nam được trải nghiệm quy trình làm việc thực tế liên tục trong suốt khóa học tại hệ thống xưởng công nghệ kỹ thuật ô tô tiêu chuẩn Nhật Bản. Được trung tâm đào tạo của các công ty tập đoàn lớn như Toyota, IGMC, vân vân và vân.",
                        ["'trải nghiệm' (nháp: 'chả nhiệm')", "'IGMC' và 'vân vân và vân' giữ nháp"], ["Toyota"]),
 "ext2_mHatGR-AoLY_7": (FIX, "và dạy nghỉ. Với chương trình đào tạo ứng dụng cùng đội ngũ giảng viên giỏi và thạo nghề, chắc chắn các kỹ sư công nghệ kỹ thuật ô tô Đại Nam tương lai sẽ trở thành một tiêu sản đón của các doanh nghiệp. Ngay bây giờ, hãy cùng ngành công nghệ kỹ thuật ô tô Trường Đại học Đại Nam trở thành một phần nguồn nhân lực ngành ô tô Việt Nam, khám phá và chinh phục những công nghệ mới nhất,",
                        ["'và dạy nghỉ', 'tiêu sản đón' giữ nháp"], ["Đại Nam"]),
 "ext2__9FWeRZBOSQ_1": (FIX, "Các kỹ sư công nghệ thực phẩm sẽ là một nhân lực quan trọng trong việc phát triển lĩnh vực này. Mụn tôi học gì ngay sau đây sẽ cung cấp thông tin cho phụ huynh và học sinh về ngành học tiềm năng này.",
                        ["'Mụn tôi học gì' giữ nháp (có thể tên chương trình)"], []),
 "ext2__9FWeRZBOSQ_2": (FIX, "và đồ uống, và tất nhiên là được thưởng thức luôn. Vui như đi chơi, nhưng lại đang học nghiêm túc về rất nhiều công nghệ thực phẩm và sức khỏe.", [], []),
 "ext2__9FWeRZBOSQ_3": (FIX, "phẩm và sức khỏe. Ngoài học ở Việt Nam những sinh viên đủ tiêu chuẩn sẽ có cơ hội sang thực tập tại Nhật Bản. \"Em đã có cơ hội cho đủ, 2 lần tại Nhật Bản, kinh nghiệm mới, tiếp xúc 19 ninh nền vặt hoà mới và đồng thời là cũng kết phạm. Tình dân nhiều bản.\" Tại các phòng thí nghiệm thực hành, sinh viên sẽ học về quá trình của thực phẩm. Các kinh nghiệm",
                        ["đoạn trích lời sinh viên giữ nháp (méo)", "'2 lần', '19' giữ nguyên"], ["Nhật Bản"]),
 "ext2__9FWeRZBOSQ_4": (LISTEN, None, ["nháp méo nặng"], ["đảm bảo chất lượng", "an toàn thực phẩm", "thực phẩm chức năng", "sức khỏe"]),
 "ext2__9FWeRZBOSQ_5": (FIX, "Nhiến, nghiên cứu viên, chuyên viên tại các viện, trung tâm phòng thí nghiệm, nghiên cứu và phát triển thực phẩm, hoặc tự mình tạo lập và phát triển doanh nghiệp trong lĩnh vực này.",
                        ["từ đầu 'Nhiến' giữ nháp"], []),
 "ext2__9FWeRZBOSQ_6": (EX, None, [HALLUCINATION], []),
 **{f"ext2_TeE0V-91_OU_{i}": (EX, None, [HALLUCINATION, "cả 8 đoạn video này chỉ ra 'Để không bỏ lỡ những video hấp dẫn'/'Đi nào?' → có thể toàn nhạc nền"], [])
    for i in range(1, 9)},
 "ext2_YNlLf8-cFao_1": (FIX, "tại Đồng Tháp, diễn ra vào sáng ngày 30/12 tại quý bay trên tỉnh Đồng Tháp, với sự tham dự của lãnh đạo hai tỉnh Đồng Tháp, dạng danh. Sau một thời gian nghiên cứu, dạc át hợp với công ty từ giấn, e.a.e. Tập đoàn Nova, NovaGroup đề xuất ý tưởng phát triển quy hoạch chung cho quên hồng ngự, dạ thành phố Hồng Ngự, dưới dự án Mekong Smart City,",
                        ["'dạng danh' có thể 'An Giang'", "'quý bay trên', 'dạc át', 'từ giấn, e.a.e.', 'quên hồng ngự' giữ nháp", "'30/12' giữ nguyên", "cờ TIME_OUTSIDE_CLIP"], ["NovaGroup", "Mekong Smart City", "Hồng Ngự", "An Giang"]),
 "ext2_YNlLf8-cFao_2": (LISTEN, None, ["tên người 'ông buổi thành nhân' — không suy đoán tên riêng từ văn bản", "cờ TIME_OUTSIDE_CLIP"], ["NovaGroup", "Đồng Tháp", "Hồng Ngự", "Đồng bằng sông Cửu Long", "thành phố thông minh kiểu mẫu"]),
 "ext2_YNlLf8-cFao_3": (LISTEN, None, ["nháp méo nhiều"], ["Đồng Tháp", "An Giang", "đột phá", "đòn bẩy", "Hồng Ngự", "đô thị kiểu mẫu", "Đồng bằng sông Cửu Long"]),
 "ext2_YNlLf8-cFao_4": (LISTEN, None, ["nháp méo nặng ('Nov. 3', 'Pluk Dragon', 'Vegas islu')", "cờ TIME_OUTSIDE_CLIP"], ["NovaGroup"]),
 "ext2_YNlLf8-cFao_5": (LISTEN, None, ["'500 mètres', '250 mètres' — đơn vị gần như chắc sai nhưng không đổi số/đơn vị từ văn bản"], ["NovaGroup", "Đồng Tháp", "An Giang", "casino", "sông Mê Kông"]),
 "ext2_YNlLf8-cFao_6": (FIX, "lãnh đạo hai tỉnh Đồng Tháp, dạng dàng, bà tỏ, sư đồng thưởng kêu. 2 tỉnh sẽ sớm có chủ trương thống nhất, từng bước thực hiện các tiểu dự án theo lộ trình, đồng thời cam kết sẽ tạo điều kiện thuận lợi để nhà đầu tư triển khai dự án.",
                        ["'dạng dàng, bà tỏ, sư đồng thưởng kêu' giữ nháp (có thể 'An Giang bày tỏ sự đồng thuận cao')", "'cam kết' (nháp 'căm cất'), 'tạo điều kiện' (nháp 'ta đưa kênh') — trung bình"], ["An Giang"]),
 "ext2_-wJIxQwbjOM_1": (EX, None, ["vòng lặp '0.0.0…' của Whisper ở nửa sau → cắt lại đoạn hoặc loại", "cờ UNKNOWN_END_TIME"], ["Nghị định số 92"]),
 "ext2_-wJIxQwbjOM_2": (FIX, "Lược sớm đi vào cuộc sống, Chính phủ đã khẩn trương ban hành Nghị định số 92, quy định chi tiết vốn nhóm, giải pháp cơ bản như sau?",
                        ["'Lược sớm' (có thể 'Để sớm'), 'vốn nhóm' giữ nháp"], ["Nghị định số 92"]),
 "ext2_-wJIxQwbjOM_3": (FIX, "2.5209 2. Miễn thuế thu nhập cá nhân, thuế giá trị gia tăng và các loại thuế khác phải nộp phát sinh từ hoạt động sản xuất kinh doanh của các tháng trong quý ba, quý bốn, năm 2024, đối với hộ, cá nhân kinh doanh. Có hoạt động sản xuất kinh doanh tại các địa bàn cấp huyện chịu tác động của dịch COVID-19 trong năm 2024.",
                        ["'2.5209 2.' đầu đoạn giữ nháp", "'năm 2024' (hai lần) GIỮ NGUYÊN nhưng nghi sai: Nghị định 92/2021 nói về năm 2021 — nghe xác nhận, không sửa theo văn bản"], ["COVID-19"]),
 "ext2_-wJIxQwbjOM_4": (LISTEN, None, ["nháp méo; mốc ngày '1/11/2021/2021', '31/2021' sai định dạng — không suy đoán"], ["thuế giá trị gia tăng", "phương pháp khấu trừ", "tỷ lệ phần trăm trên doanh thu", "tiền chậm nộp", "nợ tiền thuế"]),
 "ext2_-wJIxQwbjOM_5": (FIX, "Thế là doanh nghiệp, tổ chức, bao gồm cả đơn vị phụ thuộc, địa điểm kinh doanh, phát sinh lỗ trong kỳ tính thuế năm 2020. Nghị định này có hiệu lực thi hành kể từ ngày 19/19/2021. Việc ban hành Nghị định số 92 của Chính phủ là một bước quan trọng dằm chịt 2 kỷ thời các giải khác được quy định tại Nghị quyết số 16 của YB",
                        ["'19/19/2021' GIỮ NGUYÊN — ngày không hợp lệ, nghe xác nhận", "'Nghị quyết số 16' giữ nguyên — nghe xác nhận số hiệu", "'Thế là', 'dằm chịt 2 kỷ thời các giải khác', 'YB' giữ nháp"], ["Nghị định số 92"]),
 "ext2_-wJIxQwbjOM_6": (FIX, "Để dân vừa qua họ khăn gió tắt lợt của dịch COVID-19 để tiếp tục hoạt động sản xuất kinh doanh.",
                        ["nửa đầu giữ nháp (có thể 'giúp người dân vượt qua khó khăn do tác động')"], ["COVID-19"]),
 "ext2_Dh8IdZtdYfk_1": (FIX, "\"Đi tìm hiểu về lần của Kế toán Việt Hưng\" Hãy đăng ký kênh để theo dõi các video về thông tư, nghị định và quy định được cập nhật mới nhất hiện nay. Thông tư số không 1, năm 2020, của Bộ trưởng Bộ Tư pháp, ban hành thông tư quy định chi tiết và hướng dẫn thi hành một số điều của Nghị định số 23, năm 2015 của Chính phủ.",
                        ["'Kế toán Việt Hưng' theo tiêu đề nguồn", "'số không 1' = lời 'không một' — người duyệt chọn dạng viết theo quy ước, không trộn", "câu trích đầu giữ nháp"], ["Kế toán Việt Hưng", "Thông tư 01/2020/TT-BTP", "Nghị định số 23"]),
 "ext2_Dh8IdZtdYfk_2": (FIX, "\"Để không giá đình ông Nguyễn Văn A\" khi lấy số chứng thực bản sao, chứng minh nhân dân mang tên ông Nguyễn Văn A được ghi một số. \"Bản sao chứng minh nhân dân của bà Nguyễn Thị B được ghi một số, và bản sao sổ hộ khẩu của hộ gia đình ông Nguyễn Văn A được ghi một số.\"",
                        ["câu trích đầu giữ nháp"], []),
 "ext2_Dh8IdZtdYfk_3": (FIX, "Mỗi lạc bản dịch phải ghi một số chứng thực. Trong trường hợp này, Phòng Tư pháp sẽ lấy 3 số chứng thực, không được ghi gộp 3 việc thành một số chứng thực trong một nguyện. Khoản 3, số chứng thực hợp đồng được ghi theo từng việc, không lấy số theo lượt người yêu cầu hoặc.",
                        ["'Mỗi lạc', 'trong một nguyện' giữ nháp", "'Khoản 3' (nháp 'Quản 3')"], []),
 "ext2_Dh8IdZtdYfk_4": (FIX, "Đối với giấy tờ văn bản do Phòng Tư pháp chứng thực. Chủ tịch Ủy ban nhân dân cấp xã có thẩm quyền, ban hành quyết định hủy bỏ giá trị pháp lý của giấy tờ, văn bản đã chứng thực quy định tại khoản một điều này, đối với giấy tờ văn bản do cơ quan mình chứng thực.",
                        ["'cấp xã' giữ nháp — ngữ cảnh Phòng Tư pháp gợi ý cấp huyện, nghe xác nhận", "'đã chứng thực' (nháp 'chính thực')"], []),
 "ext2_Dh8IdZtdYfk_5": (FIX, "Bộ nguyên định pháp luật. 3. Chứng thực bản sao phải đầy đủ số trang \"e\" bản chính. Tại Điều mười, bản sao từ bản chính. Bản sao từ bản chính để chứng thực phải gồm đầy đủ các trang có thông tin của bản chính.",
                        ["'Bộ nguyên định', '\"e\"' giữ nháp"], []),
 "ext2_Dh8IdZtdYfk_6": (FIX, "Đối với quy định tại khoản 1 điều này việc chứng thực chữ ký giấy ủy quyền được thực hiện trong các trường hợp sau đây. A, ủy quyền về việc nộp hộ, nhận hộ hồ sơ, giấy tờ, trừ trường hợp pháp luật quy định không được ủy quyền. B, ủy quyền nhận hộ lớn yêu, điều phẩm.",
                        ["'lớn yêu, điều phẩm' giữ nháp (có thể 'lương hưu, bưu phẩm')", "'nộp hộ, nhận hộ hồ sơ, giấy tờ' (nháp 'nổ phộ nhận hộ hộ xơ giấy tòa') — trung bình"], []),
 "ext2_Dh8IdZtdYfk_7": (FIX, "Đi định tại Nghị định số 23/2015 của Chính phủ. Trường hợp pháp luật chuyên ngành có quy định khác về việc ghi nhận xét trên tờ khai lý lịch cá nhân thì theo pháp luật chuyên ngành. Khoản hai, người yêu cầu chứng thực phải chịu trách nhiệm về toàn bộ nội dung trong tờ khai lý lịch cá nhân của mình.",
                        ["'Đi định' giữ nháp (có thể 'Quy định')", "'về việc' (nháp 'về biểu')"], ["Nghị định số 23/2015"]),
 "ext2_Dh8IdZtdYfk_8": (FIX, "\"Đi chẳng đợi đặt thêm thủ tục. Không được gây phiền hà yêu cầu nộp thêm giấy tờ trái quy định của Nghị định số 23/2015 của Chính phủ và thông tư này.\" Những chiếc xe về điểm chính trong thông tư không một vừa rồi đã khép lại video ngày hôm nay của Kế toán Việt Hưng. Xin cảm ơn các bạn đã quan tâm chú ý lắng nghe.",
                        ["'Đi chẳng đợi', 'Những chiếc xe về' giữ nháp", "'thông tư không một' = lời 'không một'"], ["Kế toán Việt Hưng"]),
 **{f"ext2_qlt8lkh_G5k_{i}": (LISTEN, None, ["bài giảng hội thoại, nháp méo nặng"], ["dự toán xây dựng", "quản lý chi phí", "định mức", "đơn giá", "thông tư", "thẩm định", "thiết kế"])
    for i in (1, 3, 4, 6, 7, 8, 9, 10)},
 "ext2_qlt8lkh_G5k_2": (EX, None, ["vòng lặp 'thay thay thay…' (REPEATED_8_WORD_SEQUENCE) → cắt lại đoạn hoặc loại"], []),
 "ext2_qlt8lkh_G5k_5": (EX, None, ["chuỗi lặp vô nghĩa (REPEATED_8_WORD_SEQUENCE) → cắt lại đoạn hoặc loại"], []),
}


def sha(b):
    return hashlib.sha256(b).hexdigest()


def main():
    raw = PACKET.read_bytes()
    packet = json.loads(raw)
    if OUT.exists():
        raise SystemExit(f"{OUT} exists — never overwrite")
    samples = {s["sample_id"]: s for s in packet["samples"]}
    assert set(P) == set(samples) and len(P) == 60, sorted(set(P) ^ set(samples))
    records = []
    for sid, s in samples.items():
        action, text, notes, hints = P[sid]
        draft = s["initial_transcript"]
        if action == FIX and text is None:
            text = draft                       # draft already plausible: keep it, still unverified
        if action != FIX:
            assert text is None
        records.append({
            "sample_id": sid, "split": s["split"], "audio_sha256": s["audio_sha256"], "video_sha256": s["video_sha256"],
            "draft_sha256": sha(unicodedata.normalize("NFC", draft).encode("utf-8")),
            "action": action, "proposed_transcript": text, "changed_from_draft": text is not None and text != draft,
            "uncertain": notes, "term_hints": hints, "prior_feedback": s["prior_feedback"],
            "label": "CLAUDE_PROPOSED", "origin": "CLAUDE_PROPOSED", "transcript_verified": False,
        })
    payload = {
        "protocol": "claude-asr-proposal-v1",
        "status": "CLAUDE_PROPOSED review aid — NOT a label; asr_gold.validate rejects origin CLAUDE_PROPOSED",
        "method": "text-only from the Whisper drafts in packet.json; Claude did not listen to audio; numbers/dates/identifiers never changed",
        "author": "Claude (claude-opus-5-5), AI lane", "created": "2026-10-27",
        "packet": str(PACKET), "packet_file_sha256": sha(raw), "packet_sha256": packet["packet_sha256"],
        "note_on_scope": "all 60 clips covered: the 7 approved in the browser are unknown (no JSON export yet)",
        "training_ready": False, "records": records,
    }
    OUT.parent.mkdir(parents=True)
    body = json.dumps(payload, ensure_ascii=False, indent=1).encode("utf-8")
    OUT.write_bytes(body)
    count = {a: sum(r["action"] == a for r in records) for a in (EX, FIX, LISTEN)}
    print(json.dumps({"file": str(OUT), "sha256": sha(body), "counts": count,
                      "changed_from_draft": sum(r["changed_from_draft"] for r in records)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
