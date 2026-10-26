"""Render an unfilled authoring packet bound to immutable source/ASR hashes."""
import json
import sys
from pathlib import Path

from prepare_media import ROOT,OUT,sha,save
sys.path.insert(0,str(ROOT/'ai-core'))
from ai_core.tokenizer import BPETokenizer
from ai_core.training.datasets.summary_dataset import summary_prompt_ids


def render(payload):
    name = 'asr_review.html' if payload.get('protocol') == 'asr-verbatim-v1' else 'annotation.html'
    template = Path(__file__).with_name(name).read_text(encoding='utf-8')
    assert template.count('__PACKET__')==1
    return template.replace('__PACKET__',json.dumps(payload,ensure_ascii=False).replace('<','\\u003c'))


def main():
    assert not (OUT/'index.html').exists(),'Review packet already exists; never overwrite human work'
    manifest_path = ROOT/'data/manifests/minigpt_real_domain.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    assert sha(OUT/'samples.json')==manifest['samples_sha256']
    records = json.loads((OUT/'samples.json').read_text(encoding='utf-8'))
    tok = BPETokenizer.load(str(ROOT/'ai-core/checkpoints/minigpt/bpe_vocab.json'))
    samples = []
    for row in records:
        over = []
        for name,value in row['asr_inputs'].items():
            text = value['text'].strip()
            text = text.lower() if text.isupper() else text
            if not text or len(summary_prompt_ids(text,tok,'sum',512,96))!=len(tok.encode('<sum> '+text))+1:
                over.append(name)
        samples.append({**row,'over_budget_inputs':over})
    payload = {'protocol':'real-domain-human-v1','packet_sha256':manifest['samples_sha256'],'samples':samples}
    save(OUT/'packet.json',payload)
    blank = {'packet_sha256':manifest['samples_sha256'],'annotator':'','records':[
        {k:r[k] for k in ('sample_id','audio_sha256','video_sha256')} | {
            'transcript':'','summary':'','speaker_id':'','reject_reason':'','verified':False,'origin':None} for r in records]}
    save(OUT/'labels_blank.json',blank)
    (OUT/'index.html').write_text(render(payload),encoding='utf-8')
    instructions = '''# Dữ liệu mới cho MiniGPT — human labels pending

20 video mới /40 đoạn30 giây (20 phút),4 kênh mới ngoài toàn bộ10video/6kênh test cũ.
Chia theo kênh:30train/10validation; không xác nhận danh tính người nói độc lập. Điền mã người nói nếu biết; gate chặn speaker_id trùng giữa hai tập.
Giữ media gốc trong raw/youtube, source/license/attribution trong sources.json, split/time trong selection.json. CC metadata được lưu nguyên văn; không suy phiên bản giấy phép hoặc quyền từ nội dung khác. So khớp exact PCM/hash, chưa bảo đảm không trùng nội dung do đăng lại/cắt ghép.

Mở index.html hoặc http://127.0.0.1:8890/index.html. Nghe từng đoạn, tự chép lời và tự viết summary1–2câu15–35từ, chỉ nội dung nghe được. Đừng lấy title của cả video làm target của đoạn. Khi thiếu ngữ cảnh/không nghe rõ, ghi reject_reason, không đoán. Không dùng ASR máy, Whisper, MiniGPT hoặc model ngoài tạo nhãn. ASR active/candidate chỉ là noisy inputs, không phải ground truth; không có model-generated summaries trong packet.

Điền tên người viết ở đầu trang. Chỉ xác nhận sau khi nghe tiếng Việt, viết và kiểm chứng từng nhãn. Tất cả ô ban đầu trống/unchecked. Bản nháp tự lưu theo packet hash trong trình duyệt; xuất JSON để giữ file riêng. Lưu JSON hoàn tất vào thư mục này với tên human_labels_domain_v1.json.

Từ E:/traning_ai chạy:
E:/traning_ai/.venv/Scripts/python.exe dist/kaggle/kernel-minigpt-domain/import_labels.py --labels D:/data_training_ai/minigpt_domain_v1_20261019/human_labels_domain_v1.json

Gate chặn packet/media hash sai, ID thiếu/trùng, nhãn pending/reject, summary dở dang/ellipsis, tên người viết trống, nguồn/target vượt512/96BPE, split/video/channel/speaker trùng. Không cắt nhãn hoặc ngầm loại hàng. Human transcript phải đầy đủ, summary≤95BPE+EOS. Nếu sample lỗi hoặc vượt context, cần packet phiên bản mới/chia lại clip; không sửa media/split sau khi viết nhãn. Cấu trúc hợp lệ và attestation không thay thế audit nội dung độc lập.

Khi đủ nhãn, gate chỉ xuất domain_train.json/domain_val.json và provenance vào accepted_<hash>; không chạy train, không deploy, không đổi weights hoặc test set. Đây là bộ khởi đầu nhỏ, chưa chứng minh đủ dữ liệu để đạt chất lượng mục tiêu. Human labels hiện0/40; fullT1.6 chưa đạt.
'''
    (OUT/'README.md').write_text(instructions,encoding='utf-8')
    manifest.update(status='ANNOTATION_PACKET_READY_HUMAN_LABELS_PENDING',human_labels_completed=0,training_ready=False,
                    over_budget_sample_ids=[r['sample_id'] for r in samples if r['over_budget_inputs']],
                    labels_blank_sha256=sha(OUT/'labels_blank.json'),review_sha256=sha(OUT/'index.html'),
                    packet_json_sha256=sha(OUT/'packet.json'),vocab_sha256=sha(ROOT/'ai-core/checkpoints/minigpt/bpe_vocab.json'))
    save(manifest_path,manifest)
    print('ANNOTATION PACKET READY:0/40 human labels; train gate remains closed; over-budget',len(manifest['over_budget_sample_ids']))


if __name__=='__main__':
    main()
