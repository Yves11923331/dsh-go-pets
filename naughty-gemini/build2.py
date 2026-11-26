#!/usr/bin/env python3
"""顽皮的Gemini：透明表情/动作 -> 状态 GIF。

素材：trans/*.png（表情与符号都由 gpt-image-2.6-flare 画在图上）
产物：gifs/<state>.gif，pack-src/<state>.gif
"""
import os
import pathlib

import numpy as np
from PIL import Image

ROOT = pathlib.Path(__file__).parent
TRANS = ROOT / 'trans'
OUT = ROOT / 'gifs'

SIZE = 360
PAD = 20
CANVAS = SIZE + PAD * 2


def bleed_rgb(im, iters=16):
    a = np.array(im.convert('RGBA')).astype(np.float32)
    rgb, al = a[..., :3], a[..., 3]
    filled = al > 8
    if filled.any():
        rgb[~filled] = rgb[filled].mean(0)
    for _ in range(iters):
        s = np.zeros_like(rgb)
        c = np.zeros_like(al)
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            rr = np.roll(np.roll(rgb, dy, 0), dx, 1)
            ff = np.roll(np.roll(filled.astype(np.uint8), dy, 0), dx, 1)
            s += rr * ff[..., None]
            c += ff
        ok = (~filled) & (c > 0)
        rgb[ok] = s[ok] / c[ok][:, None]
        filled |= ok
    a[..., :3] = rgb
    return Image.fromarray(a.astype(np.uint8))


def face(name, alpha_gamma=None):
    im = Image.open(TRANS / f'{name}.png').convert('RGBA')
    a = np.array(im)
    a[a[..., 3] < 8, 3] = 0
    if alpha_gamma:
        al = a[..., 3].astype(np.float32) / 255.0
        a[..., 3] = (np.clip(al, 0, 1) ** alpha_gamma * 255).astype(np.uint8)
    im = bleed_rgb(Image.fromarray(a)).resize((SIZE, SIZE), Image.LANCZOS)
    c = Image.new('RGBA', (CANVAS, CANVAS), (0, 0, 0, 0))
    c.alpha_composite(im, (PAD, PAD))
    return c


def zoom_bottom(im, factor):
    w = round(im.width * factor)
    h = round(im.height * factor)
    big = im.resize((w, h), Image.LANCZOS)
    out = Image.new('RGBA', im.size, (0, 0, 0, 0))
    out.alpha_composite(big, ((im.width - w) // 2, im.height - h))
    return out


def squash(im, factor):
    """整体压扁（笑到弯腰）：保持脚底不动，上身缩短。"""
    a = np.array(im)
    ys, xs = np.nonzero(a[..., 3] > 8)
    fig = im.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))
    w = max(1, round(fig.width * factor))
    h = max(1, round(fig.height * factor))
    fig = fig.resize((w, h), Image.LANCZOS)
    canvas = Image.new('RGBA', im.size, (0, 0, 0, 0))
    bottom = int(ys.max()) + 1
    canvas.alpha_composite(fig, ((im.width - w) // 2, max(0, bottom - h)))
    return canvas


def shift(im, dy=0, dx=0):
    out = Image.new('RGBA', im.size, (0, 0, 0, 0))
    out.alpha_composite(im, (dx, dy))
    return out


def save_gif(frames, durs, path):
    def pal_of(fr):
        strip = Image.new('RGB', (fr[0].width * len(fr), fr[0].height), (40, 44, 58))
        for i, f in enumerate(fr):
            strip.paste(f.convert('RGB'), (i * f.width, 0))
        strip = strip.resize((strip.width // 4, strip.height // 4), Image.LANCZOS)
        return strip.quantize(colors=255, method=Image.FASTOCTREE, dither=Image.NONE)

    pal = pal_of(frames)
    ps = []
    for f in frames:
        p = f.convert('RGB').quantize(palette=pal, dither=Image.NONE)
        arr = np.array(p)
        arr[np.array(f.getchannel('A')) < 96] = 255
        q = Image.fromarray(arr, 'P')
        q.putpalette(pal.getpalette()[:255 * 3] + [0, 0, 0])
        ps.append(q)
    if os.path.dirname(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
    ps[0].save(path, save_all=True, append_images=ps[1:], duration=durs, loop=0,
               transparency=255, disposal=2, optimize=False)


def cycle(base, pattern, ms):
    return [shift(base, dy) for dy in pattern], [ms] * len(pattern)


def build():
    A = {}
    n = face('neutral')
    c = face('closed')

    # idle：呼吸 + 眨眼 + 小跳
    fr, du = [], []
    for dy in (0, -1, -2, -1):
        fr.append(shift(n, dy)); du.append(300)
    fr += [c, c]; du += [90, 100]
    for dy in (0, -1, -2, -1, 0):
        fr.append(shift(n, dy)); du.append(300)
    A['idle'] = (fr, du)

    # happy：开心弹跳
    h = face('happy')
    fr, du = [], []
    for dy in (0, -3, -6, -4, 0):
        fr.append(shift(h, dy)); du.append(150)
    A['happy'] = (fr, du)

    # working：1 个会话；working2：>=2 个会话（分档）
    w1, w2 = zoom_bottom(face('work1'), 1.18), zoom_bottom(face('work2'), 1.18)
    fr, du = [], []
    for i in range(6):
        fr.append(shift(w1, (0, -1)[i % 2]))
        du.append(300)
    A['working'] = (fr, du)
    fr, du = [], []
    for i in range(6):
        fr.append(shift(w2, (0, -1)[i % 2]))
        du.append(300)
    A['working2'] = (fr, du)

    A['thinking'] = cycle(face('thinking'), (0, -1, -2, -1, 0, -1), 320)
    A['error'] = ([shift(face('error'), d) for d in (0, 2, 3, 4, 4, 3)],
                  [230] * 6)
    A['notification'] = ([shift(face('notification'), 0, d) for d in (0, 2, 3, 2, 0, -2, -3, -2)],
                         [210] * 8)
    A['sleep'] = cycle(face('sleep'), (0, -1, -2, -2, -1, 0), 420)
    A['waking'] = ([face('closed'), face('closed')] +
                   [shift(face('waking'), d) for d in (0, -1, -1, 0)] +
                   [shift(n, 0)] * 2,
                   [320, 320, 300, 300, 300, 300, 320, 320])
    A['tap'] = ([shift(face('tap'), 0, d) for d in (0, 3, -3, 0)], [110] * 4)
    # done：完成——双手比耶的大星星姿势，蓄力、起跳、滞空、落地、回弹、停住
    dn = face('done2')
    done_dy = (2, -1, -6, -9, -5, 0, -2, 0)
    done_ms = (90, 70, 90, 200, 110, 90, 80, 280)
    A['done'] = ([shift(dn, dy) for dy in done_dy], list(done_ms))

    # cheer2：完成彩蛋——长大成成年形态，轻呼吸
    def grown_canvas():
        im = Image.open(ROOT / 'grown-src2' / 'gpt-20261126-085116-2.png').convert('RGBA')
        a = np.array(im)
        ys, xs = np.nonzero(a[..., 3] > 8)
        fig = im.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))
        h = CANVAS - 32
        w = max(1, round(fig.width * h / fig.height))
        fig = fig.resize((w, h), Image.LANCZOS)
        c = Image.new('RGBA', (CANVAS, CANVAS), (0, 0, 0, 0))
        c.alpha_composite(fig, ((CANVAS - w) // 2, CANVAS - 16 - h))
        return c
    g = grown_canvas()
    A['cheer2'] = ([shift(g, dy) for dy in (0, -1, -2, -1, 0, -1)],
                   [240, 220, 240, 220, 240, 300])

    A['praise'] = ([shift(face('praise'), d) for d in (0, -3, -5, -2, 0)], [140] * 5)
    A['tickle'] = ([shift(face('tickle'), 0, d) for d in (0, 2, -2, 2, -2, 0)], [120] * 6)
    A['annoyed'] = ([shift(face('annoyed'), 0, d) for d in (0, -1, 0, 1, 0)], [240] * 5)
    A['drag'] = ([shift(face('drag'), 0, d) for d in (0, 2, 0, -2, 0, 2, 0, -2)],
                 [220] * 8)

    # walk：跑动，左右摆 + 位移
    wk = face('walk')
    fr, du = [], []
    for dx in (0, 3, 5, 3, 0, -3, -5, -3):
        fr.append(shift(wk, 0, dx))
        du.append(180)
    A['walk'] = (fr, du)

    # tickle2：摸头第二段，压扁成笑到弯腰
    tk = face('tickle')
    A['tickle2'] = ([squash(tk, f) for f in (0.96, 0.91, 0.86, 0.91, 0.96, 0.93)],
                    [120] * 6)
    # juggling2：抛接·双代理，抛更高 + 轻左右摇
    jg = face('juggling')
    A['juggling2'] = ([shift(jg, dy, dx) for dy, dx in
                       ((0, 0), (-3, -2), (-5, 0), (-3, 2), (0, 0), (-2, -1), (-4, 1))],
                      [170] * 7)

    A['pout'] = cycle(face('pout'), (0, -1, -2, -1, 0), 320)
    A['yawn'] = cycle(face('yawn'), (0, -1, -2, -2, -1, 0), 380)
    A['gaze'] = cycle(face('gaze'), (0, -1, -1, 0), 340)
    A['juggling'] = ([shift(face('juggling'), 0, d) for d in (0, 2, 4, 2, 0, -2, -4, -2)],
                     [200] * 8)
    A['carrying'] = cycle(face('carrying'), (0, -1, -1, 0), 320)
    A['sweeping'] = ([shift(face('sweeping'), 0, d) for d in (0, 1, 2, 1, 0, -1, -2, -1)],
                     [220] * 8)
    return A


if __name__ == '__main__':
    anims = build()
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(ROOT / 'pack-src', exist_ok=True)
    for name, (frames, durs) in anims.items():
        save_gif(frames, durs, str(OUT / f'{name}.gif'))
        save_gif(frames, durs, str(ROOT / 'pack-src' / f'{name}.gif'))
        print(name, len(frames), 'frames', sum(durs), 'ms')
