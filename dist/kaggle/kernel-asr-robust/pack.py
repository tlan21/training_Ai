"""Freeze our Python source alongside the already prepared human-labeled dataset."""
import hashlib
import json
import zipfile
from pathlib import Path

repo = Path(__file__).resolve().parents[3]
data = Path('D:/data_training_ai/asr_robust/kaggle_dataset')
manifest = data / 'asr_robust_manifest.json'
with manifest.open('rb') as stream:
    assert hashlib.file_digest(stream, 'sha256').hexdigest() == 'e2dbb144b3ec78b265200ec05b490066ab9c04107943a833da891e1c64fb9ae3'
files = {}
with zipfile.ZipFile(data / 'ai_core.zip', 'w', compression=zipfile.ZIP_DEFLATED) as archive:
    for path in sorted((repo / 'ai-core/ai_core').rglob('*.py')):
        relative = path.relative_to(repo / 'ai-core').as_posix()
        files[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
        archive.write(path, relative)
assert files and 'ai_core/scripts/finetune_asr_robust.py' in files
with (data / 'ai_core.zip').open('rb') as stream:
    fingerprint = hashlib.file_digest(stream, 'sha256').hexdigest()
(data / 'code_manifest.json').write_text(json.dumps({'archive_sha256': fingerprint, 'files': files}, indent=2), encoding='utf-8')
print('PACKED', len(files), 'Python files; source archive SHA256', fingerprint)
