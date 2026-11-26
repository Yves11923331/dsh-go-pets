#!/usr/bin/env python3
"""遐蝶像素宠物：姿势图 -> 统一像素格 -> 带逐帧时长的动画帧。

输出：
  frames/<动画>/NN.png   帧序列
  frames/meta.json       {动画: {durs, loop}} 给 pack_build.py 打包
  preview/<动画>.gif     预览
画布固定 113x170（不随新姿势变大）。
"""
import glob
import json
import os

import numpy as np
from PIL import Image

H = 160
PAD_TOP, PAD_BOTTOM, PAD_X = 4, 6, 4
CANVAS_H = H + PAD_TOP + PAD_BOTTOM

POSES = {
    'stand':   ('assets/poses/stand.png', 160, 'bottom'),
    'poke':    ('assets/poses/poke.png', 160, 'bottom'),
    'closed':  ('assets/poses/closed.png', 160, 'bottom'),
    'sleep':   ('assets/poses/sleep.png', 128, 'bottom'),
    'think':   ('assets/poses/think.png', 160, 'bottom'),
    'work':    ('assets/poses/work.png', 160, 'bottom'),
    'error':   ('assets/poses/error.png', 160, 'bottom'),
    'cheer':   ('assets/poses/cheer.png', 146, 'top'),
    'cheer2':  ('assets/poses/cheer2.png', 160, 'top'),
    'notify':  ('assets/poses/notify.png', 160, 'bottom'),
    'wake':    ('assets/poses/wake.png', 160, 'bottom'),
    'sweep':   ('assets/poses/sweep.png', 160, 'bottom'),
    'carry':   ('assets/poses/carry.png', 160, 'bottom'),
    'juggle':  ('assets/poses/juggle.png', 160, 'bottom'),
    'praise':  ('assets/poses/praise.png', 160, 'bottom'),
    'tickle':  ('assets/poses/tickle.png', 160, 'bottom'),
    'sidework': ('assets/future/side-work.png', 156, 'bottom'),
    'annoyed': ('assets/poses/annoyed.png', 160, 'bottom'),
    'look':    ('assets/poses/look.png', 160, 'bottom'),
    'yawn':    ('assets/poses/yawn.png', 160, 'bottom'),
    'flower':  ('assets/poses/flower.png', 160, 'bottom'),
    'smile':   ('assets/poses/smile.png', 160, 'bottom'),
    'drag':    ('assets/poses/drag.png', 160, 'bottom'),
}

WALK_SHEET = 'assets/walk-sheet.png'


def crop_alpha(im):
    a = np.array(im.getchannel('A'))
    ys, xs = np.nonzero(a > 8)
    return im.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))


def harden(im):
    a = np.array(im)
    a[..., 3] = np.where(a[..., 3] >= 110, 255, 0).astype(np.uint8)
    return Image.fromarray(a, 'RGBA')


def pixelize(path, target_h):
    im = crop_alpha(Image.open(path).convert('RGBA'))
    w = max(1, round(im.width * target_h / im.height))
    return harden(im.resize((w, target_h), Image.BOX))


def split_sheet(path, expect=4):
    im = Image.open(path).convert('RGBA')
    a = np.array(im)
    cols = (a[..., 3] > 128).sum(0)
    segs, start = [], None
    for x, v in enumerate(cols > 2):
        if v and start is None:
            start = x
        if not v and start is not None:
            if x - start > 40:
                segs.append((start, x))
            start = None
    if start is not None:
        segs.append((start, len(cols)))
    if len(segs) != expect:
        raise SystemExit(f'sheet: {len(segs)} segments')
    out = []
    for x0, x1 in segs:
        part = im.crop((x0, 0, x1, im.height))
        bb = part.getchannel('A').point(lambda v: 255 if v > 8 else 0).getbbox()
        out.append(part.crop(bb))
    return out


def pixelize_scaled(im, scale):
    im = crop_alpha(im)
    return harden(im.resize((max(1, round(im.width * scale)), max(1, round(im.height * scale))), Image.BOX))


def body_anchor(im):
    a = np.array(im.getchannel('A'))
    ys, xs = np.nonzero(a > 8)
    y0, y1 = ys.min(), ys.max() + 1
    ground = ys >= y1 - max(3, int((y1 - y0) * 0.06))
    return float(xs[ground].mean())


def place(im, width, anchor='bottom', dy=0, center='body'):
    w, h = im.size
    ax = body_anchor(im) if center == 'body' else w / 2
    canvas = Image.new('RGBA', (width, CANVAS_H), (0, 0, 0, 0))
    x = round(width / 2 - ax)
    x = min(max(x, 0), width - w)
    y = CANVAS_H - PAD_BOTTOM - h if anchor == 'bottom' else PAD_TOP
    canvas.alpha_composite(im, (x, y + dy))
    return canvas


def shift(im, dy):
    if not dy:
        return im
    a = np.array(im)
    out = np.zeros_like(a)
    h = a.shape[0]
    if dy < 0:
        out[:h + dy] = a[-dy:]
        out[h + dy:] = a[h - 1]
    else:
        out[dy:] = a[:h - dy]
        out[h - dy:] = a[h - 1]
    return Image.fromarray(out, 'RGBA')


def shift_x(im, dx):
    a = np.array(im)
    out = np.zeros_like(a)
    if dx > 0:
        out[:, dx:] = a[:, :-dx]
    elif dx < 0:
        out[:, :dx] = a[:, -dx:]
    else:
        out[:] = a
    return Image.fromarray(out, 'RGBA')


def halo(im, dx, band=0.55):
    a = np.array(im)
    h, w = a.shape[:2]
    y0 = int(h * band)
    left, right = int(w * 0.18), int(w * 0.82)
    out = a.copy()
    for y in range(y0, h):
        idx = np.nonzero(a[y, :, 3] > 0)[0]
        for x in idx:
            if x < left or x > right:
                sx = x - dx
                if 0 <= sx < w:
                    out[y, x] = a[y, sx]
    return Image.fromarray(out, 'RGBA')


def glow(im, factor, box=(24, 85, 74, 108)):
    """屏幕亮度呼吸：只调笔电屏幕区域的 RGB。"""
    b = np.array(im)
    x0, y0, x1, y1 = box
    reg = b[y0:y1, x0:x1, :3].astype(float) * factor
    b[y0:y1, x0:x1, :3] = np.clip(reg, 0, 255).astype(np.uint8)
    return Image.fromarray(b, 'RGBA')


def nod(im, dy=1, cut=76):
    """头部向下点一下，颈部用上一行补。"""
    a = np.array(im)
    b = a.copy()
    b[dy:cut] = a[:cut - dy]
    b[cut - dy:cut] = a[cut - dy - 1]
    return Image.fromarray(b, 'RGBA')


def suspend(im, height=148, top=6):
    """把人物缩到更小、顶部对齐，脚下留白，做出悬空感。"""
    a = np.array(im)
    ys, xs = np.nonzero(a[..., 3] > 8)
    fig = im.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))
    w = max(1, round(fig.width * height / fig.height))
    fig = harden(fig.resize((w, height), Image.LANCZOS))
    canvas = Image.new('RGBA', (im.width, im.height), (0, 0, 0, 0))
    canvas.alpha_composite(fig, ((im.width - w) // 2, top))
    return canvas, (im.width // 2, top + 4)


def swing(im, pivot, angles, dxs):
    """绕悬挂点做钟摆，外加轻微左右平移。"""
    out = []
    for ang, dx in zip(angles, dxs):
        f = im.rotate(ang, resample=Image.NEAREST, center=pivot, expand=False)
        if dx:
            f = Image.fromarray(np.roll(np.array(f), dx, axis=1), 'RGBA')
        out.append(f)
    return out


def squash(im, factor):
    """整体压扁（笑到弯腰）：保持脚底不动，上身缩短。"""
    a = np.array(im)
    ys, xs = np.nonzero(a[..., 3] > 8)
    fig = im.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))
    w = max(1, round(fig.width * factor))
    h = max(1, round(fig.height * factor))
    fig = fig.resize((w, h), Image.NEAREST)
    b = np.array(fig)
    b[..., 3] = np.where(b[..., 3] >= 110, 255, 0).astype(np.uint8)
    fig = Image.fromarray(b, 'RGBA')
    canvas = Image.new('RGBA', im.size, (0, 0, 0, 0))
    bottom = int(ys.max()) + 1
    canvas.alpha_composite(fig, ((im.width - w) // 2, max(0, bottom - h)))
    return canvas


def main():
    px = {name: pixelize(path, th) for name, (path, th, _) in POSES.items()}

    width = max(im.width for im in px.values()) + PAD_X * 2
    sheets = split_sheet(WALK_SHEET)
    wscale = H / sheets[0].height
    walk = [place(pixelize_scaled(p, wscale), width) for p in sheets]
    full = {k: place(im, width, POSES[k][2]) for k, im in px.items()}
    full['sidework'] = place(px['sidework'], width, 'bottom', center='content')

    stand, closed = full['stand'], full['closed']
    breath1 = halo(shift(stand, -1), 1)
    breath2 = halo(shift(stand, -2), 2)

    # 呼吸 4 帧一组；眨眼两帧要快
    idle_frames = [stand, breath1, breath2, breath1,
                   stand, breath1, breath2, breath1,
                   closed, closed,
                   breath1, breath2, breath1, stand,
                   breath2, breath1]
    idle_durs = [220] * 8 + [90, 90] + [220] * 6

    think = full['think']
    thinking = [shift(think, dy) for dy in (0, -1, -2, -1, 0, -1, -2, -1)]
    work = full['work']
    working = [shift(work, dy) for dy in (0, -1, 0, -1, -2, -1, 0, -1)]
    err = full['error']
    error = [err, shift(err, 1), err, shift(err, 1), err, shift(err, 2), shift(err, 1), err]
    note = full['notify']
    notification = [note, shift_x(note, 1), shift(note, -1), shift_x(note, 1),
                    note, shift_x(note, -1), shift(note, -1), shift_x(note, -1)]
    cheer, cheer2 = full['cheer'], full['cheer2']
    done = [cheer, shift(cheer, 1), shift(cheer, 2), shift(cheer, 1),
            cheer, shift(cheer, 1), shift(cheer, 2), shift(cheer, 1)]
    bonus_cheer = [cheer2, shift(cheer2, -1), shift(cheer2, -2), shift(cheer2, -1)]
    wake, sweep, carry, juggle = full['wake'], full['sweep'], full['carry'], full['juggle']
    waking = [wake, shift(wake, -1), shift(wake, -2), shift(wake, -1), stand, stand]
    sweeping = [shift_x(sweep, d) for d in (0, 1, 2, 1, 0, -1)]
    carrying = [shift(carry, d) for d in (0, -1, 0, -1)]
    juggling = [shift(juggle, d) for d in (0, -1, -2, -1)]
    praise, tickle, annoyed = full['praise'], full['tickle'], full['annoyed']
    sw = full['sidework']
    # working2（双代理）：去掉左右位移，只留 1px 慢呼吸，避免整张桌子跟着抖
    working2 = [shift(sw, dy) for dy in (0, -1, -1, 0)]
    juggle2 = [shift_x(shift(juggle, dy), dx) for dy, dx in
               ((0, 0), (-2, -1), (-4, 0), (-3, 1), (-1, 0), (0, -1))]
    tickle2 = [shift_x(squash(tickle, f), d) for f, d in
               ((0.94, 0), (0.89, 1), (0.85, 0), (0.89, -1), (0.94, 0), (0.91, 1))]
    tap_right = [stand, praise, shift(praise, -1), praise]
    tickled = [tickle, shift_x(tickle, 1), shift(tickle, -1), shift_x(tickle, 1), tickle, shift(tickle, -1)]
    angry = [annoyed, shift_x(annoyed, -1), annoyed, shift_x(annoyed, 1), annoyed]
    look, yawn, flower, smile = full['look'], full['yawn'], full['flower'], full['smile']
    gaze = [look, shift_x(look, 1), shift(look, -1), shift_x(look, -1), look]
    idle_yawn = [shift(yawn, d) for d in (0, -1, -2, -1)]
    idle_flower = [shift(flower, d) for d in (0, -1, -2, -1)]
    bonus_smile = [shift(smile, d) for d in (0, -1, -2, -1)]
    sus, pivot = suspend(full['drag'])
    import math as _m
    angles = [0, 1.5, 2.5, 1.5, 0, -1.5, -2.5, -1.5]
    dxs = [round(3 * _m.sin(i / 8 * 2 * _m.pi)) for i in range(8)]
    dragged = swing(sus, pivot, angles, dxs)
    tap = [stand, full['poke'], full['poke'], stand]
    sleep_seq = [full['sleep'], shift(full['sleep'], -2)]

    anims = {
        'idle':         (idle_frames, idle_durs, True),
        'thinking':     (thinking, [260] * 8, True),
        'working':      (working, [100, 70, 100, 70, 100, 70, 100, 70], True),
        'done':         (done, [60, 70, 200, 90, 60, 70, 200, 90], False),
        'cheer2':       (bonus_cheer, [120, 120, 160, 120], True),
        'notification': (notification, [120, 160, 120, 160, 120, 160, 120, 160], True),
        'juggling':     (juggling, [130] * 4, True),
        'error':        (error, [90, 280, 90, 280, 90, 320, 240, 520], True),
        'sweeping':     (sweeping, [160, 140, 160, 140, 160, 140], True),
        'carrying':     (carrying, [150] * 4, True),
        'sleep':        (sleep_seq, [700, 700], True),
        'waking':       (waking, [260, 220, 260, 220, 260, 260], False),
        'walk':         (walk, [140, 130, 140, 130], True),
        'gaze':         (gaze, [260] * 5, True),
        'yawn':         (idle_yawn, [240] * 4, True),
        'flower':       (idle_flower, [240] * 4, True),
        'smile':        (bonus_smile, [200] * 4, True),
        'tap':          (tap, [70, 90, 260, 110], False),
        'praise':       (tap_right, [80, 220, 120, 80], False),
        'tickle':       (tickled, [90, 70, 90, 70, 90, 70], False),
        'tickle2':      (tickle2, [90, 70, 90, 70, 90, 90], False),
        'working2':     (working2, [220, 200, 220, 200], True),
        'juggling2':    (juggle2, [120, 100, 120, 100, 120, 100], True),
        'annoyed':      (angry, [150, 140, 150, 140, 150], False),
        'drag':         (dragged, [150] * 8, True),
    }

    meta = {}
    for name, (frames, durs, loop) in anims.items():
        assert len(frames) == len(durs), name
        d = os.path.join('frames', name)
        os.makedirs(d, exist_ok=True)
        for f in glob.glob(os.path.join(d, '*')):
            os.remove(f)
        for i, im in enumerate(frames, 1):
            im.save(os.path.join(d, f'{i:02d}.png'))
        meta[name] = {'durs': durs, 'loop': loop}
        print(name, len(frames), 'frames', frames[0].size, 'total', sum(durs), 'ms')
    with open(os.path.join('frames', 'meta.json'), 'w') as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=1)

    os.makedirs('preview', exist_ok=True)
    for f in glob.glob('preview/*.gif'):
        os.remove(f)
    for name, (frames, durs, _) in anims.items():
        zoom = 2
        w, h = frames[0].size
        gif = []
        for im in frames:
            back = Image.new('RGBA', (w, h), (246, 246, 249, 255))
            back.alpha_composite(im)
            gif.append(back.convert('RGB').resize((w * zoom, h * zoom), Image.NEAREST))
        gif[0].save(os.path.join('preview', name + '.gif'), save_all=True,
                    append_images=gif[1:], duration=durs, loop=0)
    print('canvas', width, CANVAS_H)


if __name__ == '__main__':
    main()
