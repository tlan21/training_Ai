"""Own ASR outputs are noisy model inputs, never human transcripts or targets."""
import json
import sys
import time
from pathlib import Path

from prepare_media import ROOT,OUT,sha,save
sys.path[:0] = [str(ROOT/'ai-core'),str(ROOT/'inference-service')]


def main():
    import torch
    from ai_core import build_model
    from ai_core.config import ModelConfig
    from ai_core.training.checkpoint import load_checkpoint
    from app import schemas,services
    from app.registry import registry

    assert not (OUT/'samples.json').exists(),'Final packet already frozen; do not overwrite human work'
    media = json.loads((OUT/'media_samples.json').read_text(encoding='utf-8'))
    assert len(media)==40
    manifest_path = ROOT/'data/manifests/minigpt_real_domain.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    assert sha(OUT/'media_samples.json')==manifest['media_samples_sha256']
    frozen = json.loads((OUT/'frozen_guard.json').read_text(encoding='utf-8'))
    assert all(sha(p)==h for p,h in frozen.items())
    paths = {'active':ROOT/'ai-core/checkpoints/asr_ctc/best.pt',
             'candidate':Path('D:/data_training_ai/asr_robust/outputs-v2/asr_robust_run/asr_ctc/best.pt')}
    expected = {'active':'8f87986781cfb3d4716691f2051e5798187693e2452f9f41b28ca4a753ea5531',
                'candidate':'d03ef0a962220618e90e5ff478a2fbab5ff35dd68deb539a4933eb7c15a4f3de'}
    assert all(sha(path)==expected[name] for name,path in paths.items())
    partial = OUT/'samples.partial.json'
    records = json.loads(partial.read_text(encoding='utf-8')) if partial.exists() else [{**r,'asr_inputs':{}} for r in media]
    assert [r['sample_id'] for r in records]==[r['sample_id'] for r in media]
    torch.set_num_threads(2)
    registry.device = 'cpu'
    started = time.monotonic()
    for variant,path in paths.items():
        saved = load_checkpoint(str(path))
        model = build_model(saved['config']['name'],ModelConfig(**saved['config'])).float().eval()
        model.load_state_dict(saved['state_dict'],strict=True)
        registry.models['asr_ctc'] = model
        registry.asr_vocab = saved.get('char_vocab') or saved['metadata']['char_vocab']
        assert len(registry.asr_vocab)==saved['config']['n_chars']
        del saved
        with torch.inference_mode():
            for i,row in enumerate(records,1):
                assert sha(OUT/row['audio'])==row['audio_sha256']
                if variant in row['asr_inputs']:
                    continue
                text,segments = services._real_asr(schemas.ASRRequest(audio_url=str(OUT/row['audio']),language='vi'))
                assert all(0<=s.start_time<s.end_time<=row['duration_seconds']+.02 for s in segments)
                row['asr_inputs'][variant] = {'text':text,'segments':[s.model_dump() for s in segments],
                    'checkpoint_sha256':expected[variant],'role':'NOISY_INPUT_NOT_HUMAN_REFERENCE','empty':not text.strip()}
                save(partial,records)
                print('ASR INPUT',variant,i,'/40',len(text),'chars',flush=True)
        registry.models.pop('asr_ctc')
        del model
    assert all(sha(p)==h for p,h in frozen.items())
    assert all(sha(path)==expected[name] for name,path in paths.items())
    save(OUT/'samples.json',records)
    manifest.update(status='ASR_INPUTS_PREPARED_HUMAN_LABELS_PENDING',samples_sha256=sha(OUT/'samples.json'),
                    asr_checkpoints=expected,services_sha256=sha(ROOT/'inference-service/app/services.py'),
                    asr_input_generations=80,asr_elapsed_seconds=time.monotonic()-started,
                    asr_device='cpu',asr_dtype='float32',asr_torch=torch.__version__,
                    empty_asr_inputs=sum(v['empty'] for r in records for v in r['asr_inputs'].values()))
    save(manifest_path,manifest)
    print('ASR INPUTS COMPLETE; no transcripts or summaries labeled as human.',flush=True)


if __name__=='__main__':
    main()
