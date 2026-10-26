import importlib.util
from pathlib import Path


def test_review_has_fixed_pairs_and_escapes_all_model_text():
    path = Path(__file__).with_name('run_video_pilot.py')
    spec = importlib.util.spec_from_file_location('mixed_video_pilot',path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    records = [{'sample_id':'sample_01','kind':kind,'source':'<script>bad()</script>',
                'active_summary':'<img src=x onerror=bad()>','candidate_summary':'Tiếng Việt & đúng mã'}
               for kind in module.LABELS]
    page = module.review(records,[{'sample_id':'sample_01','title':'</h2><script>bad()</script>'}])
    assert page.count('<article data-id=')==page.count('<video controls')==1
    assert page.count('class="pair"')==page.count('<details>')==3
    assert '<script>' not in page and '<img src=x' not in page
    assert '&lt;script&gt;' in page and 'Tiếng Việt &amp; đúng mã' in page
    assert 'không phải test độc lập' in page and 'không tự chấm điểm' in page.lower()
    assert '1.6/5' not in page and '<input' not in page
