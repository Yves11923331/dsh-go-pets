#!/usr/bin/env python3
"""把模型生成的透明表情（含符号）合成为状态 GIF。

素材：trans/*.png（无符号）+ symbols/*.png（模型画的符号）
产物：gifs/<state>.gif 和 pack-src/<state>.gif
"""
import os
import pathlib

import numpy as np
from PIL import Image

ROOT = pathlib.Path(__file__).parent
TRANS = ROOT / 'trans'
SYMBOLS = ROOT / 'symbols'
OUT = ROOT / os.environ.get('PET_OUT', 'gifs')
PACK = ROOT / os.environ.get('PET_PACK', 'pack-src')

SIZE = int(os.environ.get('PET_SIZE', 280))
PAD = int(os.environ.get('PET_PAD', 28))
CANVAS = SIZE + PAD * 2


def bleed_rgb(im, iters=18):
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


def load_path(path, alpha_gamma=None):
    im = Image.open(path).convert('RGBA')
    a = np.array(im)
    a[a[..., 3] < 8, 3] = 0
    if alpha_gamma:
        al = a[..., 3].astype(np.float32) / 255.0
        a[..., 3] = (np.clip(al, 0, 1) ** alpha_gamma * 255).astype(np.uint8)
    im = bleed_rgb(Image.fromarray(a)).resize((SIZE, SIZE), Image.LANCZOS)
    c = Image.new('RGBA', (CANVAS, CANVAS), (0, 0, 0, 0))
    c.alpha_composite(im, (PAD, PAD))
    return c


def face(name):
    return load_path(TRANS / f'{name}.png')


def sym(name):
    return load_path(SYMBOLS / f'{name}.png', alpha_gamma=0.35)


def shift(im, dy=0, dx=0):
    out = Image.new('RGBA', im.size, (0, 0, 0, 0))
    out.alpha_composite(im, (dx, dy))
    return out


def save_gif(frames, durs, path):
    def pal_of(fr):
        strip = Image.new('RGB', (fr[0].width * len(fr), fr[0].height), (32, 36, 44))
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

    # idle 4s：呼吸 + 眨眼
    n = face('neutral')
    c = face('closed')
    fr, du = [], []
    for dy in (0, -1, -1, 0):
        fr.append(shift(n, dy)); du.append(340)
    fr += [c, c]; du += [95, 110]
    for dy in (0, -1, -1, 0, -1, -1, 0):
        fr.append(shift(n, dy)); du.append(340)
    A['idle'] = (fr, du)

    # thinking：呼吸 + 省略号（模型画）
    A['thinking'] = cycle(sym('thinking'), (0, -1, -2, -1, 0, -1), 330)

    # working：1 个会话；working2：>=2 个会话（分档）
    w1, w2 = sym('working1'), sym('working2')
    fr, du = [], []
    for i in range(6):
        fr.append(shift(w1, (0, -1)[i % 2]))
        du.append(280)
    A['working'] = (fr, du)
    fr, du = [], []
    for i in range(6):
        fr.append(shift(w2, (0, -1)[i % 2]))
        du.append(280)
    A['working2'] = (fr, du)

    # juggling：左右小幅晃
    j = sym('juggling')
    fr, du = [], []
    for dx in (0, 3, 6, 3, 0, -3, -6, -3):
        fr.append(shift(j, 0, dx))
        du.append(230)
    A['juggling'] = (fr, du)

    # error：一下一下耷拉
    e = sym('error')
    fr, du = [], []
    for dy in (0, 2, 2, 3, 3, 4, 4, 3):
        fr.append(shift(e, dy))
        du.append(240)
    A['error'] = (fr, du)

    # done：弹跳
    d = sym('done')
    fr, du = [], []
    for dy in (0, -2, -4, -5, -4, -2, 0):
        fr.append(shift(d, dy))
        du.append(140)
    A['done'] = (fr, du)

    # notification：左右晃 + 抖
    nt = sym('notification')
    fr, du = [], []
    for dx in (0, 1, 2, 1, 0, -1, -2, -1):
        fr.append(shift(nt, 0, dx))
        du.append(220)
    A['notification'] = (fr, du)

    # sweeping：左右摆
    sw = sym('sweeping')
    fr, du = [], []
    for dx in (0, 1, 2, 1, 0, -1, -2, -1):
        fr.append(shift(sw, 0, dx))
        du.append(240)
    A['sweeping'] = (fr, du)

    # carrying：用力呼吸
    ca = sym('carrying')
    A['carrying'] = cycle(ca, (0, -1, -1, 0), 320)

    # sleep：呼吸 + Zzz
    sl = sym('sleep')
    A['sleep'] = cycle(sl, (0, -1, -2, -2, -1, 0), 420)

    # waking：闭眼 -> 迷糊（太阳）
    wk = sym('waking')
    cl = face('closed')
    fr, du = [], []
    fr += [cl, cl]; du += [340, 340]
    for dy in (0, -1, -1, 0):
        fr.append(shift(wk, dy)); du.append(320)
    fr += [shift(wk, 0)] * 2; du += [320, 320]
    A['waking'] = (fr, du)

    # walk：左右张望
    gz = face('gaze')
    gw = face('gaze')
    fr, du = [], []
    for dx in (0, 2, 3, 2, 0, -2, -3, -2):
        fr.append(shift(gz if dx >= 0 else gw, 0, dx))
        du.append(220)
    A['walk'] = (fr, du)

    # tap：惊讶 + 汗（模型画），抖一下
    tp = sym('tap')
    fr, du = [], []
    for dx in (0, 3, -3, 0):
        fr.append(shift(tp, 0, dx))
        du.append(110)
    A['tap'] = (fr, du)

    # praise：得意 + 星，弹跳
    pr = sym('praise')
    fr, du = [], []
    for dy in (0, -2, -3, -4, -2, 0):
        fr.append(shift(pr, dy))
        du.append(150)
    A['praise'] = (fr, du)

    # tickle：憋笑 + 音符，抖
    tk = sym('tickle')
    fr, du = [], []
    for dx in (0, 2, -2, 2, -2, 0):
        fr.append(shift(tk, 0, dx))
        du.append(130)
    A['tickle'] = (fr, du)

    # annoyed：不爽 + 怒气，抖
    an = sym('annoyed')
    fr, du = [], []
    for dx in (0, -1, 0, 1, 0):
        fr.append(shift(an, 0, dx))
        du.append(260)
    A['annoyed'] = (fr, du)

    # drag：慌张 + 汗，晃
    dr = sym('drag')
    fr, du = [], []
    for dx in (0, 2, 0, -2, 0, 2, 0, -2):
        fr.append(shift(dr, 0, dx))
        du.append(230)
    A['drag'] = (fr, du)

    # ---- 小剧场 ----
    ya = face('yawn')
    A['yawn'] = cycle(ya, (0, -1, -2, -2, -1, 0), 380)
    A['pout'] = cycle(sym('pout'), (0, -1, -1, 0), 320)
    A['gaze'] = cycle(face('gaze'), (0, -1, -1, 0), 340)
    A['smile'] = cycle(face('smile'), (0, -1, -1, 0), 340)

    return A


if __name__ == '__main__':
    anims = build()
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(PACK, exist_ok=True)
    for name, (frames, durs) in anims.items():
        save_gif(frames, durs, str(OUT / f'{name}.gif'))
        save_gif(frames, durs, str(PACK / f'{name}.gif'))
        print(name, len(frames), 'frames', sum(durs), 'ms')
