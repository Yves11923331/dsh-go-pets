#!/usr/bin/env python3
"""把 pack-src/*.gif 转成宠物包，补 timings/bonus，校验，打 zip。"""
import json
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).parent
SKILL = (ROOT / 'scripts-200canvas') if (ROOT / 'scripts-200canvas').exists() else pathlib.Path('/tmp/scripts200')
ID = 'naughty-gemini'
NAME = '顽皮的Gemini'
OUT = ROOT / 'out' / ID

TIMINGS = {
    'minDisplay': {'error': 1600, 'notification': 1800, 'attention': 1200,
                   'sweeping': 5600, 'carrying': 3200,
                   'working': 1000, 'thinking': 1000},
    'autoReturn': {'attention': 4000, 'error': 4800, 'sweeping': 300000, 'carrying': 3200},
    'wakeMs': 4000,
}
TIERS = {'working': [{'min': 2, 'anim': 'working2'}, {'min': 1, 'anim': 'working'}],
         'juggling': [{'min': 2, 'anim': 'juggling2'}, {'min': 1, 'anim': 'juggling'}]}
BONUS = {'attention': {'anims': ['cheer2'], 'chance': 0.3}}


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    print(r.stdout.strip())
    if r.returncode != 0:
        print(r.stderr.strip(), file=sys.stderr)
        sys.exit(r.returncode)


def main():
    tmp = pathlib.Path('/tmp/pet-pack')
    subprocess.run(['rm', '-rf', str(tmp / ID)])
    run([sys.executable, str(SKILL / 'pet_theme_convert.py'),
         '--input', str(ROOT / 'pack-src'), '--out', str(tmp),
         '--id', ID, '--input-name', NAME, '--source',
         'https://dsh.local/naughty-gemini'])
    pack_path = tmp / ID / 'pack.json'
    pack = json.loads(pack_path.read_text())
    pack['timings'] = TIMINGS
    pack['bonus'] = BONUS
    pack['tiers'] = TIERS
    if 'working2' in pack.get('animations', {}):
        pack['states']['working'] = ['working']
    if 'juggling2' in pack.get('animations', {}):
        pack['states']['juggling'] = ['juggling']
    # cheer2 是完成彩蛋，不进待机小剧场
    if 'cheer2' in pack.get('animations', {}):
        pack['idlePool']['anims'] = [a for a in pack['idlePool']['anims'] if a['anim'] != 'cheer2']
    pack_path.write_text(json.dumps(pack, ensure_ascii=False, indent=1))
    print('states', pack.get('states'), 'reactions', pack.get('reactions'))
    print('idlePool', [a['anim'] for a in pack.get('idlePool', {}).get('anims', [])])
    run([sys.executable, str(SKILL / 'pet_pack_check.py'), str(tmp / ID), '--compat-reactions'])

    OUT.mkdir(parents=True, exist_ok=True)
    zpath = OUT / f'{ID}.zip'
    import zipfile
    with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED) as z:
        for p in sorted((tmp / ID).iterdir()):
            if p.name == 'pack.json' or p.suffix == '.png':
                z.write(p, p.name)
    print('zip', zpath, zpath.stat().st_size // 1024, 'KB')


if __name__ == '__main__':
    main()
