#!/usr/bin/env python3
"""批量生成透明表情差分（gpt-image-2.6-flare，同构图只改脸）。

输出：trans/<name>.png
"""
import base64
import json
import pathlib
import sys
import time
import urllib.request
import uuid

REF = pathlib.Path('/root/workspace/maid-pet-test/ref/ref.jpg')
OUT = pathlib.Path('/root/workspace/maid-pet-test/trans')
CFG = json.loads(pathlib.Path('/root/.dsh/skills/imagegen/config.json').read_text())
G = CFG.get('gpt') or {}
KEY = G.get('api_key')
BASE = (G.get('base_url') or 'https://zdxjl.com').rstrip('/')

COMMON = (
    "保持参考图中同一角色全部细节与构图：深蓝色长卷发、蓝宝石色眼睛、白灰色蕾丝女仆头饰、"
    "两侧蓝色小蝴蝶结、白色羽翼状发饰、白色蕾丝衣领、深蓝领结与金边蓝宝石胸针。"
    "同一张半身胸像、相同位置大小和视角。背景换成完全透明的 alpha 通道，人物之外没有任何颜色，"
    "发丝、白色羽翼与白色蕾丝边缘干净完整。只改变表情："
)

FACES = {
    'working': "眉头微微下压，眼睛专注地盯着前方，嘴唇抿成一条平线，认真干活的样子，不要笑。",
    'thinking': "眉毛微皱，眼神飘向右上方，嘴唇轻抿，若有所思的样子。",
    'error': "眉毛呈八字形下垂，嘴角向下撇，眼神失焦发蔫，委屈又沮丧。",
    'done': "眼睛笑成弯弯的，嘴角明显上扬，下巴微微抬起，得意又开心。",
    'sleep': "双眼闭合，嘴唇微微张开，面部放松，睡得很沉。",
    'waking': "眼皮半睁，眼神迷迷糊糊，嘴角松垮，刚睡醒的样子。",
    'notification': "眼睛睁大发亮，视线看向右上方，嘴巴微张，像在期待什么。",
    'gaze': "眼珠转向左侧，眉毛放松，表情平静，像在望着远处。",
    'tickle': "抿着嘴憋笑，眼睛弯起来，脸颊鼓起，快要笑出声。",
    'drag': "双眼瞪大，眉头上扬，嘴巴张开，慌张又无奈。",
}

EXTRA = {
    'yawn': "闭着眼，嘴巴张得很大打哈欠，眉毛放松，一脸困意。",
    'pout': "脸颊鼓起，嘴角向下撇，眼神向旁边飘，赌气撅嘴。",
}


def gen(name, desc):
    prompt = COMMON + desc
    body = {"model": "gpt-image-2.6-flare", "prompt": prompt, "n": 1,
            "size": "1024x1024", "quality": "high", "background": "transparent"}
    boundary = "----t" + uuid.uuid4().hex
    outb = b""
    for k, v in body.items():
        outb += f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
    outb += (f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="ref.jpg"\r\n'
             f'Content-Type: image/jpeg\r\n\r\n').encode() + REF.read_bytes() + b"\r\n"
    outb += f"--{boundary}--\r\n".encode()
    req = urllib.request.Request(
        BASE + "/v1/images/edits", data=outb,
        headers={"Authorization": "Bearer " + KEY,
                 "Content-Type": "multipart/form-data; boundary=" + boundary},
        method="POST")
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=300) as r:
        d = json.loads(r.read())
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / f"{name}.png"
    p.write_bytes(base64.b64decode(d['data'][0]['b64_json']))
    print(f"{name} {time.time()-t0:.0f}s {p}", flush=True)


if __name__ == '__main__':
    todo = list(FACES.items()) + list(EXTRA.items())
    only = sys.argv[1:]
    if only:
        todo = [(k, v) for k, v in todo if k in only]
    for name, desc in todo:
        for attempt in range(2):
            try:
                gen(name, desc)
                break
            except Exception as e:
                print(f"{name} 失败({attempt+1}): {e}", flush=True)
                time.sleep(5)
