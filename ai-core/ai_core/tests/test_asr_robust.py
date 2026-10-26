import json
import tempfile
from dataclasses import asdict
from pathlib import Path

import pytest
import torch

from ai_core import build_model
from ai_core.config import ModelConfig, TrainConfig
from ai_core.scripts.prepare_asr_robust import assert_disjoint, extend_chars, normalize
from ai_core.scripts.finetune_asr_robust import BaselineGuardTrainer, RobustASRDataset, augment_audio, ctc_steps, evaluate, expand_head
from ai_core.training.checkpoint import load_checkpoint, save_checkpoint
from ai_core.training.datasets import CharVocab


def test_normalization_preserves_human_content():
    assert normalize('  tôi\tở Việt Nam 2002! ') == 'TÔI Ở VIỆT NAM 2002!'
    assert normalize('a\u0301') == 'Á'
    with pytest.raises(ValueError):
        normalize('  ')


def test_vocab_additions_train_only_preserve_ids():
    chars = extend_chars([' ', 'A', 'B'], ['AB W2'])
    assert chars[:3] == [' ', 'A', 'B']
    assert set(chars[3:]) == {'W', '2'}
    assert 'Z' not in chars  # held-out character never provided to vocabulary builder
    vocab = CharVocab(chars)
    assert vocab.decode(vocab.encode('AB W2')) == 'AB W2'


def test_split_leakage_is_rejected():
    rows = [{'split': s, 'group': s + ':1'} for s in ['train', 'val', 'test']]
    assert_disjoint(rows)
    rows[-1]['group'] = rows[0]['group']
    with pytest.raises(AssertionError):
        assert_disjoint(rows)


def test_head_expansion_keeps_backbone_and_old_rows():
    torch.manual_seed(1337)
    cfg = ModelConfig(name='asr_ctc', d_model=32, n_layers=1, n_heads=4, n_mels=16, n_chars=4)
    source = build_model('asr_ctc', cfg)
    old = {'config': asdict(cfg), 'state_dict': source.state_dict(), 'metadata': {'char_vocab': ['<blank>', ' ', 'A', 'B']}}
    target, expanded = expand_head(old, CharVocab([' ', 'A', 'B', 'W', '2']))
    assert expanded.n_chars == 6 and expanded.d_model == cfg.d_model and expanded.n_layers == cfg.n_layers
    for name, value in source.state_dict().items():
        actual = target.state_dict()[name]
        assert torch.equal(actual[:4] if name.startswith('head.') else actual, value), name
    assert torch.isfinite(target.head.weight).all()
    with pytest.raises(AssertionError):
        expand_head(old, CharVocab([' ', 'B', 'A', 'W']))


def test_audio_augmentation_seed_and_ctc_guard():
    signal = torch.linspace(-.5, .5, 16000)
    torch.manual_seed(19)
    first = augment_audio(signal, ctc_steps(len(signal)))
    torch.manual_seed(19)
    second = augment_audio(signal, ctc_steps(len(signal)))
    assert torch.equal(first, second) and torch.isfinite(first).all()
    assert ctc_steps(len(first)) >= ctc_steps(len(signal))
    assert first.abs().max() <= 1
    silent = augment_audio(torch.zeros(16000), 1)
    assert torch.count_nonzero(silent) == 0 and torch.isfinite(silent).all()


def test_initial_checkpoint_survives_worse_validation():
    model = torch.nn.Linear(2, 1)
    cfg = ModelConfig(name='asr_ctc', d_model=32, n_layers=1, n_heads=4, n_mels=16, n_chars=4)
    with tempfile.TemporaryDirectory() as temp:
        tcfg = TrainConfig(model='asr_ctc', max_steps=500, ckpt_dir=temp, log_dir='', metric_name='wer')
        path = Path(temp) / 'asr_ctc/best.pt'
        save_checkpoint(str(path), model, cfg, {'wer': .5, 'step': 0})
        trainer = BaselineGuardTrainer(model, [], None, tcfg, lambda m, b: m.weight.sum(), model_cfg=cfg, initial_metric=.5)
        assert trainer._maybe_save_best(.7, None, 500) == .5
        assert load_checkpoint(str(path))['metrics']['step'] == 0
        assert trainer._maybe_save_best(.4, .5, 1000) == .4
        assert load_checkpoint(str(path))['metrics']['step'] == 1000


def test_unalignable_training_is_reported_without_changing_manifest(tmp_path):
    path = tmp_path / 'manifest.json'
    rows = [{'path': 'good.wav', 'label': 'vi', 'split': 'train', 'group': 'train:1',
             'extra': {'transcript': 'AB', 'num_samples': 16000}},
            {'path': 'bad.wav', 'label': 'vi', 'split': 'train', 'group': 'train:2',
             'extra': {'transcript': 'AB' * 30, 'num_samples': 400}}]
    path.write_text(json.dumps({'meta': {}, 'items': rows}), encoding='utf-8')
    frozen = path.read_bytes()
    dataset = RobustASRDataset(str(path), 'train', CharVocab(['A', 'B']))
    assert len(dataset) == 1 and len(dataset.excluded) == 1
    assert dataset.excluded[0]['path'].endswith('bad.wav') and path.read_bytes() == frozen


def test_evaluation_preserves_reference_characters_outside_vocab():
    class FixedPrediction(torch.nn.Module):
        def forward(self, mel, lengths):
            return torch.tensor([[[0., 1.]]]), torch.tensor([1])

    batch = (torch.zeros(1, 80, 1), torch.tensor([1]), None, None, ['AÑ'])
    result = evaluate(FixedPrediction(), [batch], CharVocab(['A']), torch.device('cpu'), torch.float32)
    assert result['cer'] == .5 and result['predictions'][0]['reference'] == 'AÑ'
