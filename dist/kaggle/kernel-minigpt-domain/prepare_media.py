"""Prepare a small, source-separated human annotation packet; no generated labels."""
import hashlib
import json
import re
import shutil
import subprocess
import sys
import wave
from datetime import datetime,timezone
from pathlib import Path

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'dist/kaggle/kernel-minigpt-news'))
from prepare_youtube_evaluation import probe,save,sha

OUT = Path('D:/data_training_ai/minigpt_domain_v1_20261019')
FROZEN = Path('D:/data_training_ai/minigpt_real_video_20261015')
CHANNELS = ['UCfJb13P1cwuuHs5osogpTIg','UC4t0tgldykbxC-RjoGsFBeA',
            'UC7o6B2tBb9vuNIpdfgtRD3Q','UCcYAUt0vaYYcFGU_KgM7UZg']


def group_splits(channels):
    ordered = sorted(set(channels),key=lambda x:hashlib.sha256(('1337:'+x).encode()).hexdigest())
    return {c:'val' if i==0 else 'train' for i,c in enumerate(ordered)}


def pcm_sha(path):
    with wave.open(str(path)) as audio:
        return hashlib.sha256(audio.readframes(audio.getnframes())).hexdigest()


def main():
    old = json.loads((FROZEN/'sources.json').read_text(encoding='utf-8'))
    forbidden = {s['video_id'] for s in old}
    assert not set(CHANNELS) & {s['channel_id'] for s in old}
    guard_paths = [FROZEN/'sources.json',FROZEN/'evaluation/samples.json',FROZEN/'asr_ground_truth_30/references.csv',
                   *sorted((FROZEN/'evaluation').glob('ratings_rater_*.csv')),
                   ROOT/'ai-core/checkpoints/minigpt/best.pt',ROOT/'ai-core/checkpoints/asr_ctc/best.pt']
    protected = {str(p):sha(p) for p in guard_paths}
    guard = OUT/'frozen_guard.json'
    if guard.exists():
        assert json.loads(guard.read_text(encoding='utf-8'))==protected
    else:
        save(guard,protected)
    entries = {}
    for path in sorted((OUT/'discovery').glob('*.json')):
        value = json.loads(path.read_text(encoding='utf-8'))
        for row in value if isinstance(value,list) else value.get('entries',[]):
            if row.get('channel_id') in CHANNELS and 150<=(row.get('duration') or 0)<=900:
                entries[row['id']] = row
    parts = group_splits(CHANNELS)
    sources_file = OUT/'sources.json'
    sources = json.loads(sources_file.read_text(encoding='utf-8')) if sources_file.exists() else []
    for source in sources:
        assert sha(OUT/source['file'])==source['sha256'] and source['video_id'] not in forbidden
    rejected_file = OUT/'discovery/rejected.json'
    rejected = json.loads(rejected_file.read_text(encoding='utf-8'))['entries_rejected'] if rejected_file.exists() else []
    (OUT/'raw/youtube').mkdir(parents=True,exist_ok=True)
    for channel in CHANNELS:
        candidates = sorted((e for e in entries.values() if e['channel_id']==channel),
                            key=lambda e:hashlib.sha256(('1337:'+e['id']).encode()).hexdigest())
        for entry in candidates:
            if sum(s['channel_id']==channel for s in sources)>=5:
                break
            vid = entry['id']
            assert re.fullmatch(r'[A-Za-z0-9_-]{11}',vid) and vid not in forbidden
            if any(s['video_id']==vid for s in sources):
                continue
            if any(r['id']==vid for r in rejected):
                continue
            options = {'quiet':True,'no_warnings':True,'noprogress':True,'js_runtimes':{'node':{}},
                       'socket_timeout':25,'retries':2,'fragment_retries':2,'noplaylist':True,
                       'format':'bv[height<=360][vcodec^=avc1][protocol=https]+ba[ext=m4a][language^=vi][protocol=https]/bv[height<=360][vcodec^=avc1][protocol=https]+ba[ext=m4a][protocol=https]/b[height<=360][protocol=https]',
                       'merge_output_format':'mp4','outtmpl':str(OUT/'raw/youtube/%(id)s.%(ext)s'),
                       'writeinfojson':True,'writesubtitles':False,'writeautomaticsub':False}
            with YoutubeDL(options) as ydl:
                info = ydl.extract_info('https://www.youtube.com/watch?v='+vid,download=False)
                language = info.get('language')
                if ('Creative Commons' not in (info.get('license') or '') or info['channel_id']!=channel
                        or not 150<=info['duration']<=900 or (language and not language.startswith('vi'))):
                    rejected.append({'id':vid,'reason':'license/channel/duration/language','license':info.get('license'),'language':language})
                    save(OUT/'discovery/rejected.json',{'entries_rejected':rejected})
                    continue
                estimated = sum(f.get('filesize') or f.get('filesize_approx') or 0 for f in info.get('requested_formats',[info]))
                if shutil.disk_usage('D:/').free < max(estimated,150*1024**2)+1024**3:
                    raise RuntimeError('Need1GiB free reserve; preserve existing files and resume after freeing space')
                audio_languages = [f.get('language') for f in info.get('requested_formats',[]) if f.get('acodec') not in (None,'none')]
                assert all(not lang or lang.startswith('vi') for lang in audio_languages),'Avoid dubbed non-Vietnamese audio'
                try:
                    ydl.process_info(info)
                except DownloadError as error:
                    rejected.append({'id':vid,'reason':'public download unavailable','error':str(error)[:200]})
                    save(rejected_file,{'entries_rejected':rejected})
                    print('SOURCE REJECTED',vid,'public download unavailable; trying next eligible ID',flush=True)
                    continue
            media = OUT/f'raw/youtube/{vid}.mp4'
            meta = probe(media)
            assert {'video','audio'} <= {s['codec_type'] for s in meta['streams']}
            source = {'video_id':vid,'url':'https://www.youtube.com/watch?v='+vid,'channel_id':channel,
                      'channel':info['channel'],'title':info['title'],'split':parts[channel],
                      'upload_date':info.get('upload_date'),'language_metadata':language,'selected_audio_languages':audio_languages,
                      'language_human_verified':False,'license':info['license'],
                      'license_url':'https://support.google.com/youtube/answer/2797468',
                      'license_version':'Unspecified in YouTube metadata; preserve exact license label and attribution',
                      'file':media.relative_to(OUT).as_posix(),'sha256':sha(media),'bytes':media.stat().st_size,
                      'duration_seconds':float(meta['format']['duration']),'formats':info.get('format_id'),
                      'downloaded_at':datetime.now(timezone.utc).isoformat(),
                      'preservation':'Full selected source streams, remuxed without re-encoding; original retained'}
            sources.append(source)
            save(sources_file,sources)
            print('SOURCE',len(sources),'/20',vid,source['channel'],source['split'],flush=True)
        assert sum(s['channel_id']==channel for s in sources)==5,'Need five eligible sources per fixed channel'
    assert len(sources)==20 and len({s['video_id'] for s in sources})==20
    selection = {'protocol':'real-domain-human-v1','seed':1337,'channel_splits':parts,
                 'excluded_video_ids':sorted(forbidden),'excluded_channels':sorted({s['channel_id'] for s in old}),
                 'selection':'First five eligible sources per channel in seeded ID-hash order; no model outputs inspected',
                 'clips_per_video':2,'clip_seconds':30,'records':[]}
    for source in sources:
        for ordinal,start in enumerate((30,int(source['duration_seconds']*.55)),1):
            selection['records'].append({'sample_id':f'dom_{source["video_id"]}_{ordinal}','video_id':source['video_id'],
                'channel_id':source['channel_id'],'split':source['split'],'start_seconds':start,'duration_seconds':30})
    frozen_selection = OUT/'selection.json'
    if frozen_selection.exists():
        assert json.loads(frozen_selection.read_text(encoding='utf-8'))==selection
    else:
        save(frozen_selection,selection)
    original_pcm = {pcm_sha(p) for p in (FROZEN/'evaluation/audio').glob('*.wav')}
    seen_pcm,records = set(),[]
    for item in selection['records']:
        source = next(s for s in sources if s['video_id']==item['video_id'])
        paths = {kind:OUT/f'{kind}/{item["sample_id"]}.{ext}' for kind,ext in (('audio','wav'),('video','mp4'))}
        for kind,path in paths.items():
            path.parent.mkdir(exist_ok=True)
            if not path.exists():
                cmd = ['ffmpeg','-hide_banner','-loglevel','error','-n','-threads','2','-i',str(OUT/source['file']),
                       '-ss',str(item['start_seconds']),'-t','30']
                cmd += ['-vn','-ac','1','-ar','16000','-c:a','pcm_s16le'] if kind=='audio' else [
                    '-map','0:v:0','-map','0:a:0','-c:v','libx264','-threads','2','-preset','veryfast','-crf','25','-c:a','aac','-movflags','+faststart']
                subprocess.run(cmd+[str(path)],check=True)
        with wave.open(str(paths['audio'])) as audio:
            assert audio.getnchannels()==1 and audio.getframerate()==16000 and audio.getnframes()==30*16000
        assert abs(float(probe(paths['video'])['format']['duration'])-30)<.2
        fingerprint = pcm_sha(paths['audio'])
        assert fingerprint not in seen_pcm | original_pcm,'Duplicate raw PCM across packet or frozen test'
        seen_pcm.add(fingerprint)
        records.append({**item,'source_url':source['url'],'source_title':source['title'],'channel':source['channel'],
                        'source_sha256':source['sha256'],'license':source['license'],
                        **{kind:path.relative_to(OUT).as_posix() for kind,path in paths.items()},
                        **{kind+'_sha256':sha(path) for kind,path in paths.items()},'pcm_sha256':fingerprint})
    save(OUT/'media_samples.json',records)
    assert all(sha(name)==value for name,value in protected.items())
    save(ROOT/'data/manifests/minigpt_real_domain.json',{'status':'MEDIA_PREPARED_HUMAN_LABELS_PENDING','directory':str(OUT),
         'videos':20,'clips':40,'clip_seconds':30,'duration_seconds':1200,'channel_splits':parts,
         'train_clips':sum(r['split']=='train' for r in records),'val_clips':sum(r['split']=='val' for r in records),
         'sources_sha256':sha(sources_file),'selection_sha256':sha(frozen_selection),'media_samples_sha256':sha(OUT/'media_samples.json'),
         'human_labels_completed':0,'training_ready':False,'frozen_sources_excluded':10,'frozen_channels_excluded':6,
         'speaker_identity':'Unknown until human annotation; channel disjointness is a proxy, not verified speaker disjointness',
         'exact_pcm_duplicates':0,'near_duplicate_content':'Not certified; human source review still required',
         'source_bytes':sum(s['bytes'] for s in sources),'production_weights_changed':False})
    print('MEDIA PASS:20 new sources/40 clips,30train+10val, channel-disjoint, human labels still blank.',flush=True)


if __name__=='__main__':
    main()
