#!/usr/bin/env python3
"""拼总览图：每格一张动画首帧 + 中文标签（帧数取 frames/meta.json）。"""
import json
import os

from PIL import Image, ImageDraw, ImageFont

FONT = '/system/fonts/NotoSansCJK-Regular.ttc'
COLS = 8
ZOOM = 2
GAP = 12
PAD = 14
LABEL_H = 30

ORDER = [
    ('idle', '待机'), ('thinking', '思考'), ('working', '干活'), ('working2', '干活·双代理'),
    ('done', '完成'), ('cheer2', '完成彩蛋'), ('notification', '提醒'), ('juggling', '抛接'),
    ('juggling2', '抛接·双代理'), ('error', '报错'), ('sweeping', '打扫'), ('carrying', '搬运'),
    ('sleep', '睡觉'), ('waking', '醒来'), ('walk', '走路'), ('gaze', '张望'),
    ('yawn', '打哈欠'), ('flower', '摸花'), ('smile', '捧心'), ('tap', '被戳'),
    ('praise', '点赞'), ('tickle', '摸头'), ('tickle2', '摸头二段'), ('annoyed', '生气'),
    ('drag', '被拎'),
]


def main():
    meta = json.load(open('frames/meta.json', encoding='utf-8'))
    missing = [n for n, _ in ORDER if n not in meta]
    if missing:
        raise SystemExit('meta 里没有: ' + ', '.join(missing))
    firsts = {}
    for name, _ in ORDER:
        firsts[name] = Image.open(os.path.join('frames', name, '01.png')).convert('RGBA')
    w, h = firsts['idle'].size
    cw, ch = w * ZOOM, h * ZOOM
    rows = (len(ORDER) + COLS - 1) // COLS
    title_h = 44
    W = PAD * 2 + COLS * cw + (COLS - 1) * GAP
    H = PAD + title_h + rows * (ch + LABEL_H + GAP)
    sheet = Image.new('RGB', (W, H), (250, 250, 252))
    d = ImageDraw.Draw(sheet)
    title = ImageFont.truetype(FONT, 26)
    label = ImageFont.truetype(FONT, 20)
    d.text((PAD, PAD + 4), f"遐蝶 · {len(ORDER)} 个动画（分档 / 摸头二段 / 完成彩蛋 / 最短显示）",
           font=title, fill=(60, 50, 80))
    for i, (name, cn) in enumerate(ORDER):
        r, c = divmod(i, COLS)
        x = PAD + c * (cw + GAP)
        y = PAD + title_h + r * (ch + LABEL_H + GAP)
        n = len(meta[name]['durs'])
        d.text((x, y), f'{cn} {n}帧', font=label, fill=(90, 80, 110))
        back = Image.new('RGBA', (w, h), (255, 255, 255, 255))
        back.alpha_composite(firsts[name])
        sheet.paste(back.convert('RGB').resize((cw, ch), Image.NEAREST), (x, y + LABEL_H))
        d.rectangle([x - 1, y + LABEL_H - 1, x + cw, y + LABEL_H + ch],
                    outline=(228, 226, 236))
    sheet.save('out/总览.png')
    print('out/总览.png', sheet.size)


if __name__ == '__main__':
    main()
