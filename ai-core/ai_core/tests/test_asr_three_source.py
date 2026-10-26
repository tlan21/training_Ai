import copy
from types import SimpleNamespace

import pytest
import torch

from ai_core.config import ModelConfig, TrainConfig
from ai_core.scripts.finetune_asr_robust import (
    THREE_SOURCES, BaselineGuardTrainer, data_identity, guarded_selection,
    sampling_weights, validate_recipe,
)
from ai_core.training.checkpoint import load_checkpoint, save_checkpoint


def bundle():
    rows = [{'path': f'{s}/{split}.flac', 'label': 'en' if s == 'minilibrispeech' else 'vi',
             'split': split, 'group': f'{s}:{split}', 'extra': {
                 'source': s, 'transcript': 'WTO 2020', 'audio_sha256': s + split}}
            for s in THREE_SOURCES for split in ('train', 'val', 'test')]
    payload = {'meta': {'source_checkpoint_sha256': 'parent'}, 'items': rows}
    recipe = {'id': 'asr-three-source-v1', 'seed': 1337, 'steps': 2000, 'eval_every': 500,
              'initial_checkpoint_sha256': 'parent', 'vocab_sha256': 'vocab',
              'sampling_probabilities': dict(zip(THREE_SOURCES, (.4, .4, .2))),
              'data_identity_sha256': data_identity(payload),
              'selection': 'all-domain-wer-cer-nonregression-and-english-wer-improvement'}
    return payload, recipe


def test_recipe_allows_only_path_rebase():
    payload, recipe = bundle()
    validate_recipe(recipe, payload, 'vocab', 'parent', 2000)
    for row in payload['items']:
        row['path'] = '/tmp/staged/' + row['path']
    validate_recipe(recipe, payload, 'vocab', 'parent', 2000)
    for field in ('transcript', 'audio_sha256'):
        changed = copy.deepcopy(payload)
        changed['items'][0]['extra'][field] += 'changed'
        with pytest.raises(AssertionError, match='identity changed'):
            validate_recipe(recipe, changed, 'vocab', 'parent', 2000)
    payload['items'][0]['split'] = 'test'
    with pytest.raises(AssertionError, match='identity changed'):
        validate_recipe(recipe, payload, 'vocab', 'parent', 2000)


@pytest.mark.parametrize('field,value', [('seed', 99), ('steps', 4000),
    ('vocab_sha256', 'other'), ('initial_checkpoint_sha256', 'active93'),
    ('sampling_probabilities', {'vivos': .3, 'fleurs': .3, 'minilibrispeech': .4})])
def test_recipe_rejects_changed_contract(field, value):
    payload, recipe = bundle()
    recipe[field] = value
    with pytest.raises(AssertionError):
        validate_recipe(recipe, payload, 'vocab', 'parent', 2000)


@pytest.mark.parametrize('field', ['group', 'audio_sha256'])
def test_recipe_rejects_split_leakage_even_with_rehashed_rows(field):
    payload, recipe = bundle()
    a, b = payload['items'][:2]
    if field == 'group':
        b[field] = a[field]
    else:
        b['extra'][field] = a['extra'][field]
    recipe['data_identity_sha256'] = data_identity(payload)
    with pytest.raises(AssertionError, match='leakage'):
        validate_recipe(recipe, payload, 'vocab', 'parent', 2000)


def test_sampling_probability_applies_to_source_not_each_example():
    items = [SimpleNamespace(extra={'source': s}) for s, count in zip(THREE_SOURCES, (6, 1, 2)) for _ in range(count)]
    probabilities = dict(zip(THREE_SOURCES, (.4, .4, .2)))
    weights = sampling_weights(items, probabilities)
    for source, expected in probabilities.items():
        assert sum(w for i, w in zip(items, weights) if i.extra['source'] == source) == pytest.approx(expected)
    with pytest.raises(AssertionError, match='source'):
        sampling_weights(items[:-2], probabilities)


def test_guard_blocks_compensating_regression_and_requires_english_improvement():
    baseline = {s: {'wer': .5, 'cer': .2} for s in THREE_SOURCES}
    candidate = copy.deepcopy(baseline)
    assert not guarded_selection(candidate, baseline)[1]
    candidate['minilibrispeech']['wer'] = .1
    mean, eligible = guarded_selection(candidate, baseline)
    assert mean == pytest.approx(1.1 / 3) and eligible
    for source in THREE_SOURCES:
        for metric in ('wer', 'cer'):
            rejected = copy.deepcopy(candidate)
            rejected[source][metric] = baseline[source][metric] + .00001
            assert not guarded_selection(rejected, baseline)[1]
    candidate['vivos']['wer'] = float('nan')
    with pytest.raises(AssertionError, match='invalid'):
        guarded_selection(candidate, baseline)


@pytest.mark.parametrize('scores,selected_step', [([.5, .5], 0), ([.4, .5], 1)])
def test_end_of_training_preserves_baseline_or_eligible_best(tmp_path, monkeypatch, scores, selected_step):
    monkeypatch.setattr(torch.cuda, 'is_available', lambda: False)
    model = torch.nn.Linear(2, 1)
    cfg = ModelConfig(name='asr_ctc', d_model=32, n_layers=1, n_heads=4, n_mels=16, n_chars=4)
    train_cfg = TrainConfig(model='asr_ctc', max_steps=2, eval_every=1, batch_size=1, grad_accum=1,
                           lr=.01, ckpt_dir=str(tmp_path), log_dir='', metric_name='wer')
    path = tmp_path / 'asr_ctc/best.pt'
    save_checkpoint(str(path), model, cfg, {'wer': .5, 'step': 0})
    initial = path.read_bytes()
    iterator = iter(scores)
    trainer = BaselineGuardTrainer(model, [torch.ones(1, 2)], ['validation only'], train_cfg,
        lambda network, batch: network(batch).square().mean(), model_cfg=cfg,
        initial_metric=.5, compute_metric=lambda *_: next(iterator))
    trainer.train()
    assert load_checkpoint(str(path))['metrics']['step'] == selected_step
    assert load_checkpoint(str(tmp_path / 'asr_ctc/last.pt'))['metrics']['step'] == 2
    if selected_step == 0:
        assert path.read_bytes() == initial
