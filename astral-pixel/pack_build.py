#!/usr/bin/env python3
"""把 frames/ 打成 dsh-go 宠物包，并写入 tiers / bonus / timings。

复用官方 make_pet_pack 的精灵表写入与锚点/碰撞框测量，保持 crisp 像素通道，
额外补上官方 clawd 主题才会生成的 bonus（完成彩蛋）与 timings（最短显示时长）。
"""
import glob
import json
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.expanduser('~/.dsh/skills/pet-theme/scripts'))
import make_pet_pack as T  # noqa: E402

PACK_ID = 'astral-pixel'
NAME = '遐蝶'
OUT = 'out/astral-pixel'

STATES = {
    'idle': ['idle'],
    'thinking': ['thinking'],
    'working': ['working'],
    'juggling': ['juggling'],
    'error': ['error'],
    'attention': ['done'],
    'notification': ['notification'],
    'sweeping': ['sweeping'],
    'carrying': ['carrying'],
    'sleeping': ['sleep'],
    'waking': ['waking'],
    'roam': ['walk'],
}
REACTIONS = {'tapLeft': 'tap', 'tapRight': 'praise', 'tickle': 'tickle',
             'tickle2': 'tickle2', 'annoyed': 'annoyed', 'drag': 'drag'}
IDLE_POOL = ['gaze', 'yawn', 'flower', 'smile']
BONUS = {'attention': {'anims': ['cheer2'], 'chance': 0.3}}
TIMINGS = {
    'minDisplay': {'error': 1600, 'notification': 1800, 'attention': 1200,
                   'sweeping': 5600, 'carrying': 3200,
                   'working': 1000, 'thinking': 1000},
    'autoReturn': {'attention': 4000, 'error': 4800, 'sweeping': 300000, 'carrying': 3200},
}
AUTHOR = None
LICENSE = None
SOURCE = None
TIERS = {
    'working': [{'min': 2, 'anim': 'working2'}, {'min': 1, 'anim': 'working'}],
    'juggling': [{'min': 2, 'anim': 'juggling2'}, {'min': 1, 'anim': 'juggling'}],
}
ROAM = {'anim': 'walk', 'faces': 'front'}


def main():
    meta = json.load(open('frames/meta.json', encoding='utf-8'))
    anims = {}
    for name, m in meta.items():
        files = sorted(glob.glob(os.path.join('frames', name, '*.png')))
        frames = [np.array(Image.open(f).convert('RGBA')) for f in files]
        assert len(frames) == len(m['durs']), f'{name}: {len(frames)} vs {len(m["durs"])}'
        anims[name] = {'frames': frames, 'durs': m['durs'], 'loop': m['loop']}

    ch = max(f.shape[0] for a in anims.values() for f in a['frames'])
    cw = max(f.shape[1] for a in anims.values() for f in a['frames'])
    assert all(f.shape[:2] == (ch, cw) for a in anims.values() for f in a['frames'])
    hard = all(((f[..., 3] == 0) | (f[..., 3] == 255)).all()
               for a in anims.values() for f in a['frames'])

    idle_pool = [{'anim': n, 'ms': sum(anims[n]['durs']), 'weight': 1} for n in IDLE_POOL]
    awake_states = {s: STATES.get(s, []) for s in T.STATES}
    mapping = dict(states=awake_states, tiers=TIERS, reactions=REACTIONS, timings=TIMINGS,
                   idle_pool=idle_pool, bonus=BONUS, roam=ROAM,
                   sleep={'afterMs': T.SLEEP_AFTER_MS}, base_idle='idle')

    order = []
    for s in T.STATES:
        order += awake_states[s]
        if s == 'idle':
            order += IDLE_POOL
        order += BONUS.get(s, {}).get('anims', [])
    order += [REACTIONS[r] for r in T.REACTIONS if r in REACTIONS]
    order += sorted(set(anims) - set(order))
    seen = []
    for n in order:
        if n in anims and n not in seen:
            seen.append(n)

    m = T.measure(anims, 1, 'idle')
    hits, _ = T.hit_boxes(anims, 1, mapping, seen)

    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):
        if f.endswith('.png') or f == 'pack.json':
            os.remove(os.path.join(OUT, f))
    animations = {n: T.write_anim(n, anims[n], 1, OUT) for n in seen}

    wake_ms = sum(anims['waking']['durs'])
    pack = {
        'schema': 1,
        'id': PACK_ID,
        'name': NAME,
        'author': AUTHOR,
        'license': LICENSE,
        'source': SOURCE,
        'pixelArt': bool(hard),
        'scale': 1,
        'canvas': {'w': cw, 'h': ch},
        'anchor': m['anchor'],
        'contentBox': m['contentBox'],
        'hitBoxes': hits,
        'animations': animations,
        'idlePool': {'everyMs': dict(T.IDLE_EVERY_MS), 'anims': idle_pool},
        'states': awake_states,
        'bonus': BONUS,
        'tiers': TIERS,
        'timings': dict(TIMINGS, wakeMs=wake_ms),
        'reactions': REACTIONS,
        'roam': ROAM,
        'sleep': {'afterMs': T.SLEEP_AFTER_MS},
    }
    with open(os.path.join(OUT, 'pack.json'), 'w', encoding='utf-8') as fh:
        fh.write(T.dumps(pack) + '\n')

    frames = sum(len(a['durs']) for a in anims.values())
    total = sum(os.path.getsize(os.path.join(OUT, f)) for f in os.listdir(OUT))
    print(f'{len(animations)} animations, {frames} frames, {total // 1024} KB, canvas {cw}x{ch}')
    print('states', sorted(awake_states))
    print('bonus', BONUS, 'timings', TIMINGS, 'tiers', TIERS)


if __name__ == '__main__':
    main()
