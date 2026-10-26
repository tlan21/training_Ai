"""Plot verified replay output; stdout losses are rounded, validation metrics exact."""
import json
import re
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[3]
OUT = Path('D:/data_training_ai/minigpt_news/mixed_replay_output_v1')


def main():
    report = json.loads((OUT/'verification.json').read_text(encoding='utf-8'))
    assert report['kernel']=='traininghighlight/ai-core-minigpt-replay-v1'
    log = OUT/'ai-core-minigpt-replay-v1.log'
    try:
        text = log.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        text = log.read_text(encoding='cp1252')
    entries = json.loads(text)
    text = ''.join(entry['data'] for entry in entries)
    text = text[text.index('stage mixed steps 300'):]
    losses = [{'step':int(step),'loss':float(loss)}
              for step,loss in re.findall(r'\[train\] step (\d+)/300 \| loss ([\d.]+)',text)]
    assert [x['step'] for x in losses]==[1]+list(range(15,301,15))
    rounds = report['validation_rounds']
    assert [x['step'] for x in rounds]==[60,120,180,240,300]
    fig, axes = plt.subplots(2,2,figsize=(13,7.6),constrained_layout=True)
    ax = axes[0,0]
    ax.plot([x['step'] for x in losses],[x['loss'] for x in losses],color='#6535a1')
    ax.set(title='Mixed 1:1 training loss (rounded stdout)',ylabel='Cross entropy')
    for ax,key,title in ((axes[0,1],'rouge_l','Summary ROUGE-L'),
                         (axes[1,0],'cap_hit','Output cap hit rate (lower is better)'),
                         (axes[1,1],'repeated_trigram_fraction','Repeated trigram fraction (lower is better)')):
        for name,color,label in (('sum_clean','#326cb3','Clean'),('sum_asr','#c46a22','Synthetic ASR')):
            ax.plot([r['step'] for r in rounds],[r['formats'][name][key] for r in rounds],
                    marker='o',color=color,label=label)
            ax.axhline(report['baseline_metrics'][name][key],ls='--',color=color,alpha=.7,label=label+' init')
        if key=='rouge_l':
            ax.plot([r['step'] for r in rounds],[r['selection_score'] for r in rounds],color='#555555',ls=':',label='Paired mean')
            chosen = report['selected_round']
            if chosen:
                ax.scatter([chosen['step']],[chosen['selection_score']],marker='*',s=180,color='#27824c',label='Selected (guard passed)',zorder=5)
        ax.set(title=title,ylim=(0,1))
        ax.legend(fontsize=8,ncol=2)
    for ax in axes.flat:
        ax.set_xlabel('Optimizer update')
        ax.grid(alpha=.2)
    fig.suptitle(f"MiniGPT mixed replay: {report['eligible_rounds']}/5 eligible rounds; not deployed",fontsize=14)
    for suffix in ('png','svg'):
        fig.savefig(ROOT/f'docs/T1.6_mixed_replay_curves.{suffix}',dpi=160)
    plt.close(fig)
    (ROOT/'docs/T1.6_mixed_replay_curve_data.json').write_text(json.dumps({
        'loss_precision':'rounded stdout; final exact loss in training_result.json',
        'train_loss':losses,'validation_rounds':rounds,'baseline_metrics':report['baseline_metrics']},indent=2)+'\n',encoding='utf-8')
    print('Curves PASS:21 train-loss points /5 exact validation rounds, PNG+SVG+data')


if __name__=='__main__':
    main()
