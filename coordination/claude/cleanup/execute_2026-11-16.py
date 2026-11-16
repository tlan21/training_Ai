"""AI-08 round 3 step 5: delete ONLY the approved manifest paths (groups given on argv). Before each delete, re-check:
duplicates still match their kept copy (sha256), file-listed dirs still match the recorded file list. Any mismatch -> stop.
  python execute.py <CLEANUP_2026-11-16.json> A B C
"""
import hashlib
import json
import os
import sys


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def files(path):
    if os.path.isfile(path):
        return [path]
    return sorted(os.path.join(r, f) for r, _, fs in os.walk(path) for f in fs)


man = json.load(open(sys.argv[1], encoding='utf-8'))
freed = 0
for g in sys.argv[2:]:
    for it in man['groups'][g]['items']:
        path, kept = it['path'], it['kept_copy']
        if not os.path.exists(path):
            print(f'{g} already gone {path}')
            continue
        fl = files(path)
        if not fl and os.path.isdir(path):  # resume: files deleted in an interrupted run, only empty dirs left
            for r, _, _ in os.walk(path, topdown=False):
                os.rmdir(r)
            freed += it['bytes']
            print(f'{g} removed empty dirs (files deleted earlier) {it["bytes"]:>13,} B  {path}', flush=True)
            continue
        if sum(os.path.getsize(f) for f in fl) != it['bytes']:
            sys.exit(f'STOP size changed: {path}')
        if kept:
            for f in fl:
                ref = kept if os.path.isfile(kept) else os.path.join(kept, os.path.basename(f))
                if sha(f) != sha(ref):
                    sys.exit(f'STOP not identical to kept copy: {f}')
        else:
            rec = it['files_sha256']
            now = {os.path.relpath(f, path).replace('\\', '/'): [os.path.getsize(f), sha(f)] for f in fl}
            if now != rec:
                sys.exit(f'STOP file list changed: {path}')
        for f in fl:
            os.remove(f)
        if os.path.isdir(path):  # remove now-empty subdirs bottom-up, then the dir itself; never a parent
            for r, _, _ in os.walk(path, topdown=False):
                os.rmdir(r)
        freed += it['bytes']
        print(f'{g} deleted {len(fl):4d} files {it["bytes"]:>13,} B  {path}', flush=True)
print(f'FREED {freed:,} B')
