"""Private ASR candidate run; legacy two-source or frozen three-source recipe."""
import hashlib
import json
import shutil
import sys
import zipfile
from pathlib import Path
from unittest.mock import patch


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def extract(archive, destination):
    with zipfile.ZipFile(archive) as bundle:
        for name in bundle.namelist():
            assert '\\' not in name and (destination / name).resolve().is_relative_to(destination.resolve()), name
        bundle.extractall(destination)


def one(root, pattern):
    found = list(root.rglob(pattern))
    assert len(found) == 1, (pattern, len(found))
    return found[0]


def audio_root(parent, folder, relative):
    anchor = Path(*Path(relative).parts[1:])
    found = [p for p in parent.rglob(folder) if p.is_dir() and (p / anchor).is_file()]
    assert len(found) == 1, (folder, len(found))
    return found[0]


def stage_audio(root, data, payload, staging):
    original = one(root, 'vivos.json')
    assert sha(original) == payload['meta']['vivos_manifest_sha256']
    legacy = one(root, 'asr_robust_manifest.json').parent
    archives = [(legacy, 'fleurs_audio', 'fleurs_archive_sha256'),
                (original.parent, 'vivos_waves', 'vivos_archive_sha256')]
    if any(i['extra']['source'] == 'minilibrispeech' for i in payload['items']):
        archives.append((data, 'english_audio', 'english_archive_sha256'))
    for parent, folder, fingerprint in archives:
        archive = parent / (folder + '.zip')
        if archive.exists():
            assert sha(archive) == payload['meta'][fingerprint]
            extract(archive, staging)
        else:
            relative = next(i['path'] for i in payload['items'] if i['path'].startswith(folder + '/'))
            source = audio_root(parent, folder, relative)
            shutil.copytree(source, staging / folder)
    for item in payload['items']:
        relative = Path(item['path'])
        assert not relative.is_absolute() and '..' not in relative.parts and '\\' not in item['path']
        target = staging / relative
        assert target.is_file()
        if 'audio_sha256' in item['extra']:
            assert sha(target) == item['extra']['audio_sha256']
        item['path'] = str(target)
    manifest = staging / 'manifest.json'
    manifest.write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')
    return manifest


def main():
    root = Path('/kaggle/input')
    three = list(root.rglob('asr_three_source_manifest.json'))
    assert len(three) <= 1, 'ambiguous three-source packet'
    manifest_source = three[0] if three else one(root, 'asr_robust_manifest.json')
    data = manifest_source.parent
    recipe = json.loads((data / 'recipe.json').read_text(encoding='utf-8')) if three else None
    expected = recipe['manifest_sha256'] if recipe else 'e2dbb144b3ec78b265200ec05b490066ab9c04107943a833da891e1c64fb9ae3'
    assert sha(manifest_source) == expected
    code_manifest = json.loads((data / 'code_manifest.json').read_text(encoding='utf-8'))
    staging = Path('/tmp/asr_three_source' if three else '/tmp/asr_robust')
    staging.mkdir(parents=True, exist_ok=False)
    if (data / 'ai_core.zip').exists():
        assert sha(data / 'ai_core.zip') == code_manifest['archive_sha256']
        extract(data / 'ai_core.zip', staging)
        package = staging / 'ai_core'
    else:
        package = one(data, 'finetune_asr_robust.py').parents[1]
    assert package.name == 'ai_core' and (package / '__init__.py').is_file()
    for relative, fingerprint in code_manifest['files'].items():
        assert sha(package.parent / relative) == fingerprint, relative
    sys.path.insert(0, str(package.parent))
    payload = json.loads(manifest_source.read_text(encoding='utf-8'))
    manifest = stage_audio(root, data, payload, staging)

    import torch
    from ai_core.tests.test_gradient_check import test_rmsnorm_gradient, test_swiglu_gradient, test_mha_gradient
    from ai_core.tests.test_adamw_parity import test_adamw_parity_linear_regression
    from ai_core.tests.test_ctc_parity import test_ctc_loss_parity
    from ai_core.tests.test_overfit_one_batch import test_overfit_one_batch_asr_ctc
    from ai_core.training.datasets import CharVocab
    torch.set_num_threads(2)
    assert torch.cuda.is_available(), 'CUDA required'
    print('GPU', torch.cuda.get_device_name(), 'TORCH', torch.__version__, flush=True)
    for check in (test_rmsnorm_gradient, test_swiglu_gradient, test_mha_gradient):
        check()
    print('SANITY gradient <1e-4 PASS', flush=True)
    test_adamw_parity_linear_regression()
    print('SANITY own AdamW parity <1e-6 PASS', flush=True)
    test_ctc_loss_parity()
    with patch('torch.cuda.is_available', return_value=False):
        test_overfit_one_batch_asr_ctc()
    print('SANITY own CTC parity + ASR one-batch loss <0.05 PASS', flush=True)
    vocab = CharVocab(json.loads((data / 'robust_vocab.json').read_text(encoding='utf-8'))['chars'])
    if recipe:
        from ai_core.scripts.finetune_asr_robust import validate_recipe
        validate_recipe(recipe, payload, sha(data / 'robust_vocab.json'), sha(data / 'source_asr.pt'), recipe['steps'])
    for item in payload['items']:
        if item['split'] == 'train':
            text = item['extra']['transcript']
            assert vocab.decode(vocab.encode(text)) == text
    print('SANITY training char-vocab roundtrip100% PASS (MiniGPT/BPE unchanged)', flush=True)
    from ai_core.scripts.finetune_asr_robust import main as train
    sys.argv = ['finetune_asr_robust', '--manifest', str(manifest), '--initial', str(data / 'source_asr.pt'),
                '--vocab', str(data / 'robust_vocab.json'), '--output', '/kaggle/working/asr_three_source_run' if three else '/kaggle/working/asr_robust_run',
                '--steps', str(recipe['steps']) if recipe else '4000']
    if recipe:
        sys.argv += ['--recipe', str(data / 'recipe.json')]
    train()


if __name__ == '__main__':
    main()
