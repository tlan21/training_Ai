import json
from types import SimpleNamespace

import pytest
import torch

from ai_core.scripts.finetune_asr_robust import ReferenceASRDataset, collate_references, evaluate
from ai_core.scripts.prepare_asr_robust import normalize
from ai_core.scripts.train import _build_loaders
from ai_core.training.datasets import ASRDataset, CharVocab


@pytest.mark.parametrize('text', ['FTA', 'WTO', '2020', '9.4%', '08-NQ/TW', 'A\u0301'])
def test_encode_refuses_unknown_symbols_instead_of_shortening_text(text):
    vocab = CharVocab(list('ATONQ4 '))
    with pytest.raises(ValueError, match=r'cannot encode characters:.*U\+'):
        vocab.encode(text)


def test_lossless_normalization_and_existing_ids():
    text = normalize('  Hà Nội\tFTA WTO 08-NQ/TW 9,4% 2020 a\u0301 ')
    assert text == 'HÀ NỘI FTA WTO 08-NQ/TW 9,4% 2020 Á'
    old = CharVocab([' ', 'A', 'B'])
    assert old.encode('AB BA') == [2, 3, 1, 3, 2]
    vocab = CharVocab.from_transcripts([text])
    assert vocab.decode(vocab.encode(text)) == text
    assert old.encode('') == []


def manifest(tmp_path, train='AB', val='AB'):
    path = tmp_path/'labels.json'
    rows = [{'path': f'{split}_not_loaded.wav', 'split': split, 'group': split,
             'extra': {'transcript': text}} for split, text in [('train', train), ('val', val)]]
    path.write_text(json.dumps({'meta': {}, 'items': rows}), encoding='utf-8')
    return path


@pytest.mark.parametrize('text', ['AF', '', '  ', None])
def test_train_preflight_fails_with_sample_context_before_audio_loading(tmp_path, text):
    path = manifest(tmp_path, train=text)
    with pytest.raises(ValueError, match='ASR train sample.*train_not_loaded.wav'):
        ASRDataset(str(path), 'train', CharVocab(['A', 'B']))


def test_generic_validation_keeps_unseen_reference_without_growing_vocab(tmp_path, monkeypatch):
    path = manifest(tmp_path, val='AÑ')
    vocab = tmp_path/'vocab.json'
    vocab.write_text(json.dumps({'chars': ['A', 'B']}), encoding='utf-8')
    args = SimpleNamespace(manifest=str(path), vocab=str(vocab))
    cfg = SimpleNamespace(n_mels=80)
    _, validation, metadata, metric = _build_loaders('asr_ctc', cfg, SimpleNamespace(batch_size=1), args)
    monkeypatch.setattr(validation.dataset, '_load_audio', lambda _: torch.zeros(16000))
    assert next(iter(validation))[-1] == ['AÑ']
    assert metadata['char_vocab'] == ['<blank>', 'A', 'B'] and cfg.n_chars == 3

    class Prediction(torch.nn.Module):
        def forward(self, mel, lengths):
            return torch.tensor([[[0., 1., 0.]]]), torch.tensor([1])

    assert metric(Prediction(), validation, torch.device('cpu')) == 1.


def test_held_out_oov_survives_dataset_and_metric_without_encoding(tmp_path, monkeypatch):
    path = manifest(tmp_path, val='AÑ')
    vocab = CharVocab(['A', 'B'])
    data = ReferenceASRDataset(str(path), 'val', vocab)
    monkeypatch.setattr(data, '_load_audio', lambda _: torch.zeros(16000))
    mel, targets, text = data[0]
    assert mel.shape[0] == 80 and targets.numel() == 0 and text == 'AÑ'
    batch = collate_references([(mel, targets, text)])

    class Prediction(torch.nn.Module):
        def forward(self, mel, lengths):
            return torch.tensor([[[0., 1., 0.]]]), torch.tensor([1])

    result = evaluate(Prediction(), [batch], vocab, torch.device('cpu'), torch.float32)
    assert result['cer'] == .5 and result['wer'] == 1.
    assert result['predictions'][0]['reference'] == 'AÑ'


@pytest.mark.parametrize('split,augment', [('train', False), ('val', True)])
def test_reference_loader_cannot_be_used_for_training_or_augmentation(tmp_path, split, augment):
    with pytest.raises(ValueError, match='held-out data without augmentation'):
        ReferenceASRDataset(str(manifest(tmp_path)), split, CharVocab(['A', 'B']), augment=augment)
